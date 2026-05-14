mod cli;
mod app;
mod infra;

use clap::Parser;

fn main() {
    let args = cli::Cli::parse();
    match args.command {
        cli::Command::Get { entity_id } => {
            let repo = infra::ha_repo::HaRepository::new();
            let state = repo.get_sensor(entity_id);
            println!("{state}");
        }
        cli::Command::Set { entity_id, value } => {
            let repo = infra::ha_repo::HaRepository::new();
            repo.set_sensor(entity_id, value);
        }
        cli::Command::CalendarEvents => {
            let service = app::prompts_service::PromptsService::new();
            let events = service.get_calendar_events();
            for event in events {
                println!("{event}");
            }
        }
        cli::Command::DailyPrompt => {
            let service = app::prompts_service::PromptsService::new();
            let prompt = service.generate_daily_prompt();
            println!("{prompt}");
        }
    }
}
