"""
Audio utilities for the podcast generator service.
Contains classes for managing audio paths and stitching audio segments.
"""

import logging
import os
from typing import List, Tuple, Optional, Dict
from pathlib import Path

from pydub import AudioSegment
from app.podcast_models import DialogueTurn
from .storage_utils import ensure_directory_exists

logger = logging.getLogger(__name__)

class AudioPathManager:
    """Handles path creation and management for podcast audio files."""
    
    def __init__(self, base_output_dir: str = "./outputs"):
        self.base_output_dir = base_output_dir
        
    def create_podcast_directories(self, podcast_id: str) -> Tuple[str, str]:
        """
        Creates directory structure for a podcast and returns paths.
        
        Args:
            podcast_id: Unique identifier for the podcast
            
        Returns:
            Tuple of (podcast_dir, segments_dir)
        """
        podcast_dir = os.path.join(self.base_output_dir, "audio", podcast_id)
        segments_dir = os.path.join(podcast_dir, "segments")
        
        ensure_directory_exists(podcast_dir)
        ensure_directory_exists(segments_dir)
        
        return podcast_dir, segments_dir
        
    def get_segment_path(self, podcast_id: str, turn_id: int) -> str:
        """
        Get path for a specific dialogue turn audio file.
        
        Args:
            podcast_id: Unique identifier for the podcast
            turn_id: ID of the dialogue turn
            
        Returns:
            Path to the audio segment file
        """
        return os.path.join(self.base_output_dir, "audio", podcast_id, 
                           "segments", f"turn_{turn_id:03d}.mp3")
                           
    def get_final_audio_path(self, podcast_id: str) -> str:
        """
        Get path for the final stitched audio file.
        
        Args:
            podcast_id: Unique identifier for the podcast
            
        Returns:
            Path to the final audio file
        """
        return os.path.join(self.base_output_dir, "audio", podcast_id, "final.mp3")


class AudioStitchingService:
    """Handles the generation and stitching of audio segments."""
    
    def __init__(self, tts_service, path_manager: AudioPathManager):
        """
        Initialize the AudioStitchingService.
        
        Args:
            tts_service: Text-to-speech service instance
            path_manager: AudioPathManager instance for managing file paths
        """
        self.tts_service = tts_service
        self.path_manager = path_manager
        self.logger = logging.getLogger(__name__)
    
    async def generate_audio_for_dialogue_turn(self, 
                                         turn: DialogueTurn, 
                                         podcast_id: str,
                                         persona_details_map: dict,
                                         persona_research_map: Optional[Dict[str, 'PersonaResearch']] = None) -> Tuple[bool, str]:
        """
        Generate audio for a single dialogue turn.
        
        Args:
            turn: The dialogue turn to generate audio for
            podcast_id: Unique identifier for this podcast
            persona_details_map: Map of speaker IDs to details (for gender)
            
        Returns:
            Tuple of (success_bool, audio_file_path)
        """
        try:
            # Get the output path for this turn
            output_path = self.path_manager.get_segment_path(podcast_id, turn.turn_id)
            
            # Initialize variables for TTS parameters
            speaker_gender = None
            voice_name = None
            voice_params = None
            
            # PRIORITY 1: Check PersonaResearch objects first (new approach)
            if persona_research_map and turn.speaker_id in persona_research_map:
                persona = persona_research_map[turn.speaker_id]
                if persona.gender:
                    speaker_gender = persona.gender
                if persona.tts_voice_id:
                    voice_name = persona.tts_voice_id
                if hasattr(persona, 'tts_voice_params') and persona.tts_voice_params:
                    voice_params = persona.tts_voice_params
                
                log_msg = f"[AUDIO_STITCH] Using PersonaResearch data for {turn.speaker_id}: gender={speaker_gender}, voice={voice_name}"
                if voice_params:
                    log_msg += f", params={voice_params}"
                self.logger.info(log_msg)
            
            # PRIORITY 2: Fall back to persona_details_map (legacy approach) - DEPRECATED
            elif turn.speaker_id in persona_details_map:
                speaker_gender = persona_details_map[turn.speaker_id].get("gender")
                self.logger.warning(f"[AUDIO_STITCH] DEPRECATED: Using persona_details_map for {turn.speaker_id}: gender={speaker_gender}. Please migrate to PersonaResearch objects.")
            
            # PRIORITY 3: Use turn.speaker_gender as last resort
            if not speaker_gender and turn.speaker_gender:
                speaker_gender = turn.speaker_gender
                self.logger.warning(f"[AUDIO_STITCH] Falling back to turn.speaker_gender={turn.speaker_gender} for {turn.speaker_id}")
            
            # If we still don't have a gender, log it clearly
            if not speaker_gender:
                self.logger.warning(f"[AUDIO_STITCH] No gender information found for {turn.speaker_id}! Defaulting to system default.")
            
            self.logger.info(f"[AUDIO_STITCH] Generating audio for turn {turn.turn_id} (speaker: {turn.speaker_id}, gender: {speaker_gender})")
            
            # Generate audio using TTS service with all available parameters
            success = await self.tts_service.text_to_audio_async(
                text_input=turn.text,
                output_filepath=output_path,
                speaker_gender=speaker_gender,
                voice_name=voice_name,
                voice_params=voice_params
            )
            
            if success:
                self.logger.info(f"[AUDIO_STITCH] Generated audio for turn {turn.turn_id} at {output_path}")
                return True, output_path
            else:
                self.logger.error(f"[AUDIO_STITCH] Failed to generate audio for turn {turn.turn_id}")
                return False, ""
                
        except Exception as e:
            self.logger.error(f"[AUDIO_STITCH] Error generating audio for turn {turn.turn_id}: {str(e)}", exc_info=True)
            return False, ""
    
    async def stitch_audio_segments(self, 
                              segment_paths: List[str], 
                              output_path: str,
                              silence_duration_ms: int = 500) -> bool:
        """
        Stitch multiple audio segments with silence between them.
        
        Args:
            segment_paths: List of paths to audio segments
            output_path: Path to save the stitched audio
            silence_duration_ms: Duration of silence between segments in milliseconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not segment_paths:
                self.logger.error("[AUDIO_STITCH] No audio segments provided for stitching")
                return False
            
            self.logger.info(f"[AUDIO_STITCH] Starting audio stitching of {len(segment_paths)} segments")
            
            # Create the output directory if needed
            ensure_directory_exists(os.path.dirname(output_path))
            
            # Create silence segment
            silence = AudioSegment.silent(duration=silence_duration_ms)
            
            # Load the first segment
            try:
                combined = AudioSegment.from_mp3(segment_paths[0])
                self.logger.info(f"[AUDIO_STITCH] Loaded first segment: {segment_paths[0]}")
            except Exception as e:
                self.logger.error(f"[AUDIO_STITCH] Failed to load first segment: {e}", exc_info=True)
                return False
            
            # Add remaining segments with silence in between
            for i, path in enumerate(segment_paths[1:], 1):
                try:
                    segment = AudioSegment.from_mp3(path)
                    combined = combined + silence + segment
                    self.logger.info(f"[AUDIO_STITCH] Added segment {i+1}: {path}")
                except Exception as e:
                    self.logger.error(f"[AUDIO_STITCH] Failed to add segment {i+1}: {e}", exc_info=True)
                    # Continue with remaining segments
            
            # Export the combined audio
            combined.export(output_path, format="mp3")
            self.logger.info(f"[AUDIO_STITCH] Successfully exported stitched audio to {output_path}")
            return True
            
        except ImportError as e:
            self.logger.error(f"[AUDIO_STITCH] Missing pydub library: {e}", exc_info=True)
            return False
        except Exception as e:
            self.logger.error(f"[AUDIO_STITCH] Error during audio stitching: {e}", exc_info=True)
            return False
