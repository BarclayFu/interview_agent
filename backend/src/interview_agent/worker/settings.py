"""arq Worker 配置：并发=1（spec §5.9，3C2G 控内存）。"""

from arq.connections import RedisSettings

from interview_agent.worker.tasks import parse_resume


class WorkerSettings:
    functions = [parse_resume]
    max_jobs = 1
    job_timeout = 300

    @staticmethod
    def redis_settings() -> RedisSettings:
        from interview_agent.core.config import get_settings

        return RedisSettings.from_dsn(get_settings().redis_url)
