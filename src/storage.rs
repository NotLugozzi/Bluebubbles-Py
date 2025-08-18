use crate::api::models::Conversation;
use directories::ProjectDirs;
use rusqlite::{params, Connection, OptionalExtension};
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

fn db_path() -> Option<PathBuf> {
    let proj = ProjectDirs::from("com", "example", "BlueBubblesGTK")?;
    let dir = proj.data_dir().to_path_buf();
    Some(dir.join("cache.sqlite"))
}

fn ensure_dir(path: &PathBuf) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    Ok(())
}

fn open_conn() -> rusqlite::Result<Connection> {
    let path = db_path().ok_or_else(|| rusqlite::Error::InvalidPath("no data dir".into()))?;
    let _ = ensure_dir(&path);
    Connection::open(path)
}
// Caching chats and messages to speed up load times and reduce api queries
pub fn init() -> Result<(), String> {
    let conn = open_conn().map_err(|e| e.to_string())?;
    conn.execute_batch(
        r#"
        PRAGMA journal_mode = WAL;
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            raw_json TEXT
        );
        "#,
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}

pub fn upsert_chats(chats: &[Conversation], raws: Option<&[serde_json::Value]>) -> Result<(), String> {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_secs() as i64;
    let mut conn = open_conn().map_err(|e| e.to_string())?;
    let tx = conn.transaction().map_err(|e| e.to_string())?;
    for (idx, c) in chats.iter().enumerate() {
        let raw = raws
            .and_then(|r| r.get(idx))
            .map(|v| serde_json::to_string(v).unwrap_or_default());
        tx.execute(
            r#"
            INSERT INTO chats (id, name, updated_at, raw_json)
            VALUES (?1, ?2, ?3, ?4)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                updated_at=excluded.updated_at,
                raw_json=excluded.raw_json
            "#,
            params![c.id, c.name, now, raw],
        )
        .map_err(|e| e.to_string())?;
    }
    tx.commit().map_err(|e| e.to_string())?;
    Ok(())
}

pub fn get_chats(limit: Option<usize>) -> Result<Vec<Conversation>, String> {
    let conn = open_conn().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare(
            "SELECT id, name FROM chats ORDER BY updated_at DESC, name ASC LIMIT ?1",
        )
        .map_err(|e| e.to_string())?;
    let lim = limit.unwrap_or(500) as i64;
    let rows = stmt
        .query_map(params![lim], |row| {
            Ok(Conversation {
                id: row.get(0)?,
                name: row.get(1)?,
            })
        })
        .map_err(|e| e.to_string())?;
    let mut out = Vec::new();
    for r in rows {
        out.push(r.map_err(|e| e.to_string())?);
    }
    Ok(out)
}

pub fn last_chat_updated_at(id: &str) -> Result<Option<i64>, String> {
    let conn = open_conn().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT updated_at FROM chats WHERE id = ?1")
        .map_err(|e| e.to_string())?;
    let ts: Option<i64> = stmt
        .query_row(params![id], |row| row.get(0))
        .optional()
        .map_err(|e| e.to_string())?;
    Ok(ts)
}
