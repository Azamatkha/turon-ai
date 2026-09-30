import logging

from celery import Celery
from celery.schedules import crontab
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from loggers import get_logger
from src.main.config import config

logger = get_logger(__name__)


# Har daqiqada ishlaydigan "uy tozalash" tasklari. Celery har bir ishga
# tushishni 3 qator bilan yozadi (beat: "Sending due task", worker:
# "received", "succeeded") — ya'ni kuniga ~4300 ma'nosiz qator. Task o'zi
# natija bo'lgandagina (nimadir o'chirilganda) log yozadi (qara:
# src/user/tasks.py).
_QUIET_TASKS = ("cleanup_unverified_users",)


class _QuietTaskFilter(logging.Filter):
    """Shovqinli tasklarning FAQAT INFO/DEBUG qatorlarini yashiradi. Xato va
    ogohlantirishlar ("raised unexpected", retry) baribir chiqadi."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.WARNING:
            return True
        msg = record.getMessage()
        return not any(name in msg for name in _QUIET_TASKS)


# Filtr shu loggerlarning O'ZI yaratgan yozuvlariga qo'llanadi: beat
# jadvalchisi, worker'ning "received" va "succeeded" qatorlari.
for _name in ("celery.beat", "celery.worker.strategy", "celery.app.trace"):
    logging.getLogger(_name).addFilter(_QuietTaskFilter())


redis_url = config.redis.dsn
rabbitmq_url = config.rabbitmq.dsn

# Async DB engine and session
engine = create_async_engine(config.postgres.dsn_async)
local_async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

celery_app = Celery(__name__, broker=rabbitmq_url, backend=redis_url)

celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.update(
    task_create_missing_queues=True,
    task_acks_late=True,
    task_send_sent_event=True,
    task_track_started=True,
    task_time_limit=1800,
    task_always_eager=False,  # False for async task execution
)

celery_app.conf.update(
    include=[
        "src.user.tasks",
        "src.core.email_service.tasks",
        "src.knowledge.tasks",
        "src.notifications.tasks",
    ],
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    # Tasdiqlanmagan akkaunt ro'yxatdan o'tganiga 24 soat to'lishi bilan
    # o'chsin — HAR DAQIQADA tekshiramiz (kechikish eng ko'pi 1 daqiqa).
    # Har soatlik tekshiruvda user 1 soatgacha ortiqcha turib qolardi.
    #
    # Nega har bir user uchun "24 soatdan keyin o'chir" (ETA/countdown) taski
    # EMAS: Celery bunday taskni 24 soat davomida tasdiqlanmagan RabbitMQ
    # xabari sifatida ushlab turadi, RabbitMQ esa sukut bo'yicha 30 daqiqadan
    # uzoq kutgan xabarda ulanishni uzadi (consumer_timeout). Daqiqalik
    # tekshiruvda bu muammo yo'q, narxi esa daqiqasiga bitta kichik SQL.
    "cleanup_unverified_users_every_minute": {
        "task": "cleanup_unverified_users",
        "schedule": crontab(),
    },
    # Valyuta kurslarini har kuni yangilab turamiz.
    # Celery timezone = UTC, Toshkent = UTC+5 => 11:00 Toshkent = 06:00 UTC.
    "scrape_exchange_rates_daily_11_tashkent": {
        "task": "scrape_exchange_rates",
        "schedule": crontab(minute=0, hour=6),
    },
    # Eskirgan bildirishnomalarni har kuni kechasi tozalaymiz.
    "cleanup_old_notifications_daily": {
        "task": "cleanup_old_notifications",
        "schedule": crontab(minute=30, hour=3),
    },
}
