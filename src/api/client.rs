use reqwest::Client as HttpClient;
use tokio_tungstenite::connect_async;
use url::Url;
use crate::api::models::Conversation;
use serde_json::Value;

pub struct ApiClient {
    pub http: HttpClient,
    pub ws_url: Option<Url>,
}

impl ApiClient {
    pub fn new() -> Self {
        Self {
            http: HttpClient::new(),
            ws_url: None,
        }
    }

    pub async fn login(&self, server: &str, username: &str, password: &str) -> Result<(), String> {
        Ok(())
    }

    pub async fn connect_ws(&self, ws_url: &str) -> Result<(), String> {
        let url = Url::parse(ws_url).map_err(|e| e.to_string())?;
        let (ws_stream, _) = connect_async(url).await.map_err(|e| e.to_string())?;
        println!("WebSocket connected");
        Ok(())
    }

    fn base_api(base_url: &str) -> String {
        let trimmed = base_url.trim_end_matches('/');
        if trimmed.ends_with("/api") { trimmed.to_string() } else { format!("{}/api", trimmed) }
    }

    fn with_auth<'a>(mut req: reqwest::RequestBuilder, token: Option<&'a str>, password: Option<&'a str>) -> reqwest::RequestBuilder {
        if let Some(t) = token {
            req = req.header("Authorization", format!("Bearer {}", t));
        }
        if let Some(p) = password {
            req = req.header("password", p);
        }
        req
    }

    /// Try to reach the BlueBubbles server using common ping endpoints.
    /// Sends the token or password header when provided.
    pub async fn ping(&self, base_url: &str, token: Option<&str>, password: Option<&str>) -> Result<u16, String> {
        let base_api = Self::base_api(base_url);
        let candidates = [format!("{}/v1/ping", base_api), format!("{}/ping", base_api), format!("{}", base_url.trim_end_matches('/'))];
        let mut last_err: Option<String> = None;
        for endpoint in candidates {
            let req = Self::with_auth(self.http.get(&endpoint), token, password);
            match req.send().await {
                Ok(resp) => return Ok(resp.status().as_u16()),
                Err(e) => last_err = Some(e.to_string()),
            }
        }
        Err(last_err.unwrap_or_else(|| "Failed to reach any endpoint".into()))
    }

    /// Fetch conversations/chats from the server using BlueBubbles chat query endpoint.
    /// Returns minimal Conversation list and the raw JSON items for caching.
    pub async fn conversations(&self, base_url: &str, password: &str) -> Result<(Vec<Conversation>, Vec<Value>), String> {
        let base = base_url.trim_end_matches('/');
        let endpoint = format!("{}/api/v1/chat/query?password={}", base, password);
        let body = serde_json::json!({
            "limit": 1000,
            "offset": 0,
            "with": ["lastMessage", "sms", "archived"],
            "sort": "lastmessage"
        });

        match self.http.post(&endpoint).json(&body).send().await {
            Ok(resp) => {
                if !resp.status().is_success() {
                    return Err(format!("HTTP {}", resp.status()));
                }
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let items = if let Some(arr) = json.as_array() {
                            arr.clone()
                        } else if let Some(arr) = json.get("chats").and_then(|v| v.as_array()) {
                            arr.clone()
                        } else if let Some(arr) = json.get("data").and_then(|v| v.as_array()) {
                            arr.clone()
                        } else {
                            Vec::new()
                        };
                        let mut out = Vec::new();
                        for item in &items {
                            let id = item.get("id").and_then(|v| v.as_str()).unwrap_or_default().to_string();
                            let name = item.get("name")
                                .or_else(|| item.get("display_name"))
                                .or_else(|| item.get("title"))
                                .or_else(|| item.get("displayName"))
                                .and_then(|v| v.as_str())
                                .unwrap_or("Chat").to_string();
                            if !id.is_empty() {
                                out.push(Conversation { id, name });
                            }
                        }
                        Ok((out, items))
                    }
                    Err(e) => Err(e.to_string()),
                }
            }
            Err(e) => Err(e.to_string()),
        }
    }

    pub async fn obtain_token(&self, base_url: &str, password: &str) -> Result<String, String> {
        let base_api = Self::base_api(base_url);
        let candidates = [
            format!("{}/v1/login", base_api),
            format!("{}/v1/auth", base_api),
            format!("{}/login", base_api),
            format!("{}/auth", base_api),
        ];
        let mut last_err: Option<String> = None;
        for endpoint in candidates {
            let req = self.http.post(&endpoint).header("password", password);
            match req.send().await {
                Ok(resp) => {
                    if !resp.status().is_success() {
                        last_err = Some(format!("HTTP {}", resp.status()));
                        continue;
                    }
                    match resp.json::<Value>().await {
                        Ok(json) => {
                            if let Some(tok) = json.get("token").and_then(|v| v.as_str()) {
                                return Ok(tok.to_string());
                            }
                            if let Some(tok) = json.get("accessToken").and_then(|v| v.as_str()) {
                                return Ok(tok.to_string());
                            }
                            last_err = Some("Token not found in response".into());
                        }
                        Err(e) => last_err = Some(e.to_string()),
                    }
                }
                Err(e) => last_err = Some(e.to_string()),
            }
        }
        Err(last_err.unwrap_or_else(|| "Failed to obtain token".into()))
    }

    /// Fetch contacts for the "New Chat" UI. Returns a simple list of contact entries.
    pub async fn contacts(&self, base_url: &str, password: &str) -> Result<Vec<crate::api::models::ContactEntry>, String> {
        let base = base_url.trim_end_matches('/');
        let endpoint = format!("{}/api/v1/contact?password={}", base, password);
        let resp = self.http.get(&endpoint).send().await.map_err(|e| e.to_string())?;
        if !resp.status().is_success() {
            return Err(format!("HTTP {}", resp.status()));
        }
        let json: Value = resp.json().await.map_err(|e| e.to_string())?;
        let list = json.as_array().cloned()
            .or_else(|| json.get("data").and_then(|v| v.as_array()).cloned())
            .unwrap_or_default();
        let mut out = Vec::new();
        for c in list {
            let name = c.get("displayName").or_else(|| c.get("name")).and_then(|v| v.as_str()).unwrap_or("");
            let address = c.get("address").or_else(|| c.get("phone")).or_else(|| c.get("email")).or_else(|| c.get("id")).and_then(|v| v.as_str()).unwrap_or("");
            if !address.is_empty() {
                let label = if name.is_empty() { address.to_string() } else { format!("{} ({})", name, address) };
                out.push(crate::api::models::ContactEntry { label, address: address.to_string() });
            }
        }
        Ok(out)
    }

    pub async fn create_chat(&self, base_url: &str, password: &str, addresses: Vec<String>, message: Option<String>) -> Result<Conversation, String> {
        let base = base_url.trim_end_matches('/');
        let endpoint = format!("{}/api/v1/chat/new?password={}", base, password);
        let body = serde_json::json!({
            "addresses": addresses,
            "message": message.unwrap_or_default(),
        });
        let resp = self.http.post(&endpoint).json(&body).send().await.map_err(|e| e.to_string())?;
        if !resp.status().is_success() {
            return Err(format!("HTTP {}", resp.status()));
        }
        let json: Value = resp.json().await.map_err(|e| e.to_string())?;
        let id = json.get("guid").or_else(|| json.get("id")).and_then(|v| v.as_str()).unwrap_or_default().to_string();
        if id.is_empty() {
            return Err("No chat GUID in response".into());
        }
        let name = json.get("name").or_else(|| json.get("displayName")).and_then(|v| v.as_str()).unwrap_or("Chat").to_string();
        Ok(Conversation { id, name })
    }
}
