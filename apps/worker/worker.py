import os
import time

import structlog
from redis import Redis

log = structlog.get_logger()
redis = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

while True:
    redis.set("lava:worker:heartbeat", int(time.time()), ex=30)
    log.info("worker_heartbeat")
    time.sleep(10)

