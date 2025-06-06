import pytest
from unittest.mock import patch

from app.tts_service import GoogleCloudTtsService, texttospeech

class FakeVoice:
    def __init__(self, name, lang, gender):
        self.name = name
        self.language_codes = [lang]
        self.ssml_gender = gender

class FakeResponse:
    def __init__(self, voices):
        self.voices = voices


def _generate_fake_voices():
    voices = []
    for i in range(12):
        voices.append(FakeVoice(f"en-US-Chirp3-HD-M{i}", "en-US", texttospeech.SsmlVoiceGender.MALE))
    for i in range(4):
        voices.append(FakeVoice(f"en-GB-Chirp3-HD-M{i}", "en-GB", texttospeech.SsmlVoiceGender.MALE))
    for i in range(4):
        voices.append(FakeVoice(f"en-AU-Chirp3-HD-M{i}", "en-AU", texttospeech.SsmlVoiceGender.MALE))
    for i in range(12):
        voices.append(FakeVoice(f"en-US-Chirp3-HD-F{i}", "en-US", texttospeech.SsmlVoiceGender.FEMALE))
    for i in range(4):
        voices.append(FakeVoice(f"en-GB-Chirp3-HD-F{i}", "en-GB", texttospeech.SsmlVoiceGender.FEMALE))
    for i in range(4):
        voices.append(FakeVoice(f"en-AU-Chirp3-HD-F{i}", "en-AU", texttospeech.SsmlVoiceGender.FEMALE))
    return voices


def test_voice_cache_distribution(tmp_path):
    voices = _generate_fake_voices()
    fake_client = type("FakeClient", (), {"list_voices": lambda self: FakeResponse(voices)})()
    cache_file = tmp_path / "cache.json"
    with patch("app.tts_service.texttospeech.TextToSpeechClient", return_value=fake_client):
        with patch.object(GoogleCloudTtsService, "VOICE_CACHE_FILE", str(cache_file)):
            service = GoogleCloudTtsService()
            cache = service._load_or_refresh_voice_cache(force_refresh=True)

    assert sum(len(cache[g]) for g in cache) == 60
    for gender in ["Male", "Female", "Neutral"]:
        assert len(cache[gender]) == 20

    def lang_count(lc):
        return sum(1 for g in cache for v in cache[g] if lc in v["language_codes"])

    assert lang_count("en-US") == 36
    assert lang_count("en-GB") == 12
    assert lang_count("en-AU") == 12

    combos = {(v["voice_id"], v["speaking_rate"]) for g in cache for v in cache[g]}
    assert len(combos) <= 50  
    assert len(combos) >= 30  

    male_ids = {v["voice_id"] for v in cache["Male"]}
    female_ids = {v["voice_id"] for v in cache["Female"]}
    male_in_neutral = sum(1 for v in cache["Neutral"] if v["voice_id"] in male_ids)
    female_in_neutral = sum(1 for v in cache["Neutral"] if v["voice_id"] in female_ids)
    assert male_in_neutral == female_in_neutral == 10
