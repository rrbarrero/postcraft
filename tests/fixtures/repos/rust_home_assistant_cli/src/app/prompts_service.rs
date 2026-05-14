use crate::infra::ha_repo::HaRepository;

pub struct PromptsService {
    repo: HaRepository,
}

impl PromptsService {
    pub fn new() -> Self {
        Self {
            repo: HaRepository::new(),
        }
    }

    pub fn get_calendar_events(&self) -> Vec<String> {
        self.repo.fetch_calendar_events()
    }

    pub fn generate_daily_prompt(&self) -> String {
        let events = self.get_calendar_events();
        let sensors = self.repo.list_sensors();
        format!(
            "Today's events: {}. Active sensors: {}.",
            events.len(),
            sensors.len()
        )
    }
}
