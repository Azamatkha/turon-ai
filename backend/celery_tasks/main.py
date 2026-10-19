from celery import Celery
from celery.schedules import crontab
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from loggers import get_logger
from src.main.config import config

logger = get_logger(__name__)


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
        "src.core.email_service.tasks",
        "src.knowledge.tasks",
        "src.notifications.tasks",
    ],
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    # Tasdiqlanmagan akkauntlar avtomatik O'CHIRILMAYDI: xodimlar tashqi
    # tizimdan `is_verified=false` holida ommaviy yuklanadi va hamma ham
    # Face-ID'dan tez o'ta olmaydi. Bunday userni faqat admin o'chiradi.
    # Valyuta kurslari: bank kursni ertalab 09:00 dan e'lon qila boshlaydi va
    # uzog'i 12:00 gacha yangilab bo'ladi — shu oraliqda HAR YARIM SOATDA
    # tekshiramiz: 09:05, 09:35, ... 12:05, 12:35 (Toshkent).
    # Celery timezone = UTC, Toshkent = UTC+5 => 04–07 UTC soatlari.
    # Ilgari kuniga bir marta (11:00) edi: kurs 09:00 da chiqsa ham bizda 11:00
    # gacha kechagisi turardi, vazifa o'sha payt yiqilsa — ertagacha.
    # Tez-tez ishlatish xavfsiz: kurs o'zgarmagan bo'lsa vazifa hech narsa
    # yozmaydi va bildirishnoma yubormaydi (knowledge/tasks.py -> _same_rates).
    "scrape_exchange_rates_morning_half_hourly": {
        "task": "scrape_exchange_rates",
        "schedule": crontab(minute="5,35", hour="4-7"),
    },
    # Eskirgan bildirishnomalarni har kuni kechasi tozalaymiz.
    "cleanup_old_notifications_daily": {
        "task": "cleanup_old_notifications",
        "schedule": crontab(minute=30, hour=3),
    },
}
