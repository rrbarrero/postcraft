use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "ha-client")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand)]
pub enum Command {
    /// Read a sensor state
    Get { entity_id: String },
    /// Set a sensor state
    Set { entity_id: String, value: String },
    /// Fetch calendar events
    CalendarEvents,
    /// Generate a daily prompt
    DailyPrompt,
}
