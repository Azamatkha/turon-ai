#!/bin/sh
# Postgres zaxira nusxasi — `backup` konteyneri (docker-compose.yml).
#
# Ilova obrazidagi pg_dump 15-versiya, server esa PostgreSQL 18: eski pg_dump
# yangi serverni dump qilmaydi. Shuning uchun nusxani postgres:18 obrazidan
# yasalgan shu kichik konteyner oladi (yangi obraz yuklab olinmaydi).
#
# Har kuni BACKUP_HOUR:00 da (konteyner TZ bo'yicha) pg_dump -Fc oladi,
# BACKUP_KEEP_DAYS kundan eskilarini o'chiradi (eng so'nggisi doim qoladi).
# Ishga tushganda bugungi nusxa bo'lmasa — darhol oladi.
#
# Tiklash (misol):
#   pg_restore -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists db_YYYYMMDD_HHMMSS.dump

set -u

DIR=/backups/postgres
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
HOUR="${BACKUP_HOUR:-2}"

# Dump'lar maxfiy: faqat egasi (root) o'qiy oladi. Ilova (appuser) faqat
# ro'yxat va hajmni ko'radi — buning uchun papkaga 755 kifoya.
umask 077
mkdir -p "$DIR" /backups/qdrant
chmod 755 /backups "$DIR"
# Qdrant snapshot'ini Celery (appuser, root emas) yozadi va eskisini o'chiradi —
# uning uid'i obrazga bog'liq, shuning uchun papka hammaga yoziladigan, lekin
# "sticky" (1777): har kim faqat o'z faylini o'chira oladi.
chmod 1777 /backups/qdrant

status() {
    echo "$1 $(date -u +%Y-%m-%dT%H:%M:%S+00:00)" > "$DIR/last_status"
}

run_backup() {
    ts=$(date +%Y%m%d_%H%M%S)
    part="$DIR/.db_$ts.dump.part"
    echo "[backup] pg_dump boshlandi: $ts"
    if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h "${POSTGRES_HOST:-postgres}" \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -Z 6 -f "$part"; then
        # Yarim yozilgan fayl hech qachon "tayyor nusxa" bo'lib ko'rinmasin
        mv "$part" "$DIR/db_$ts.dump"
        status ok
        echo "[backup] tayyor: db_$ts.dump ($(du -h "$DIR/db_$ts.dump" | cut -f1))"
    else
        rm -f "$part"
        status fail
        echo "[backup] XATO: pg_dump muvaffaqiyatsiz" >&2
    fi
    # Rotatsiya: eskilarini o'chiramiz, lekin eng so'nggisi doim qoladi
    newest=$(ls -1t "$DIR"/db_*.dump 2>/dev/null | head -n 1)
    find "$DIR" -name 'db_*.dump' -mtime +"$KEEP_DAYS" ! -path "$newest" -delete
}

# Postgres tayyor bo'lguncha kutamiz
until pg_isready -h "${POSTGRES_HOST:-postgres}" -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
    sleep 5
done

today=$(date +%Y%m%d)
if ! ls "$DIR"/db_"$today"_*.dump >/dev/null 2>&1; then
    run_backup
fi

while true; do
    now=$(date +%s)
    next=$(date -d "today ${HOUR}:00" +%s)
    if [ "$next" -le "$now" ]; then
        next=$(date -d "tomorrow ${HOUR}:00" +%s)
    fi
    sleep $((next - now))
    run_backup
done
