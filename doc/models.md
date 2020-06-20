Список моделей для базы данных.

На данный момент в качестве базы данных выбрана SQLite3 (модуль Python: `sqlite3`).

Какие точно будут модели?

1. ~~Пользователь~~.
2. ~~Обсуждение~~.
3. ~~Комментарий~~.
4. ~~Инвайт-код~~.
5. ~~Уведомление~~.

# ~~Пользователь~~

- `email`
- `name`
- `password`
- `avatar`
- `status`
- `rating`
- `id`
- `description`
- `badges`
- `blocked`
- `moderator`

# ~~Обсуждение~~

- `title`
- `content`
- `date`
- `id`
- `owner`
- `up`
- `down`
- `views`

# ~~Комментарий~~

- `content`
- `date`
- `owner`
- `thread_id`
- `id`
- `up`
- `down`

# ~~Инвайт-код~~

- `code`
- `owner`
- `valid`

# ~~Уведомление~~

- `owner`
- `date`
- `title`
- `content`
- `type`
- `icon`
- `href`
