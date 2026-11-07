from .enums import StepStatus
from .logger import get_logger
from .services.step_service import StepService

logger = get_logger("JobContext")


class JobContext:
    def __init__(self, job_id: int, step_service: StepService) -> None:
        self.job_id = job_id
        self.step_service = step_service

    def step(self, step_name: str):
        def decorator_step(func):
            async def wrapper(*args, **kwargs):
                logger.debug(f"Выполнение шага {step_name}.")
                step = await self.step_service.get_by_job_and_name(
                    self.job_id, step_name
                )

                if not step:
                    step = await self.step_service.create(self.job_id, step_name)

                if step.status == StepStatus.COMPLETED:
                    logger.debug(f"Данные шага {step_name} получены из базы.")
                    return step.result
                else:
                    await self.step_service.update_status(step.id, StepStatus.RUNNING)

                    try:
                        result = await func(*args, **kwargs)
                    except Exception:
                        await self.step_service.update_status(
                            step.id, StepStatus.FAILED
                        )
                        raise

                    logger.debug(f"Данные получены путем выполнения шага {step_name}.")
                    await self.step_service.update_status_and_result(
                        step.id, StepStatus.COMPLETED, result
                    )

                    return result

            return wrapper

        return decorator_step
