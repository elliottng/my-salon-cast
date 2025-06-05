#!/usr/bin/env python3
import asyncio
import json
import datetime
from app.mcp_server import get_task_status

class MockCtx:
    def __init__(self):
        self.request_id = 'test'
        self.client_info = {'name': 'test', 'version': '1.0', 'environment': 'test'}

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)

async def main():
    # Check status of our task (use the task ID from our test run)
    task_id = '84e4ac2c-1d99-4a8e-aedd-92660c1b4325'
    status = await get_task_status(ctx=MockCtx(), task_id=task_id)
    print(json.dumps(status, indent=2, cls=DateTimeEncoder))

if __name__ == "__main__":
    asyncio.run(main())
