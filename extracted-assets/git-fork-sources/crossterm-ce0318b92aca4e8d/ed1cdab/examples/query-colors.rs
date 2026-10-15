use std::io;

use crossterm::style::{query_background_color, query_foreground_color};

fn main() -> io::Result<()> {
    print_color("Foreground", query_foreground_color()?);
    print_color("Background", query_background_color()?);
    Ok(())
}

fn print_color(label: &str, color: Option<crossterm::style::Color>) {
    match color {
        Some(value) => println!("{label}: {:?}", value),
        None => println!("{label}: (unrecognized response)"),
    }
}
