use std::collections::HashMap;

pub struct HaRepository {
    base_url: String,
    token: String,
}

impl HaRepository {
    pub fn new() -> Self {
        Self {
            base_url: "http://homeassistant.local:8123".to_string(),
            token: String::new(),
        }
    }

    pub fn get_sensor(&self, entity_id: String) -> String {
        format!("sensor {entity_id} state: 22.5")
    }

    pub fn set_sensor(&self, entity_id: String, value: String) {
        println!("set {entity_id} = {value}");
    }

    pub fn list_sensors(&self) -> Vec<String> {
        vec!["temperature".to_string(), "humidity".to_string()]
    }

    pub fn fetch_calendar_events(&self) -> Vec<String> {
        vec![
            "Meeting at 10:00".to_string(),
            "Lunch at 12:30".to_string(),
        ]
    }
}
