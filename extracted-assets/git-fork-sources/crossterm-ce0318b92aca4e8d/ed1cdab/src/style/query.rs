use std::io;

use crate::style::Color;

#[cfg(all(unix, feature = "events"))]
use std::{fs::File, io::Write, time::Duration};

#[cfg(all(unix, feature = "events"))]
use crate::{
    event::{
        filter::OscColorFilter,
        internal::{self, InternalEvent, OscColorPayload},
    },
    terminal::{disable_raw_mode, enable_raw_mode},
};

/// Query the terminal for its current foreground color.
#[cfg(all(unix, feature = "events"))]
pub fn query_foreground_color() -> io::Result<Option<Color>> {
    query_color_slot(10)
}

/// Query the terminal for its current background color.
#[cfg(all(unix, feature = "events"))]
pub fn query_background_color() -> io::Result<Option<Color>> {
    query_color_slot(11)
}

#[cfg(all(unix, feature = "events"))]
fn query_color_slot(slot: u8) -> io::Result<Option<Color>> {
    if crate::terminal::sys::is_raw_mode_enabled() {
        query_color_slot_raw(slot)
    } else {
        enable_raw_mode()?;
        let result = query_color_slot_raw(slot);
        disable_raw_mode()?;
        result
    }
}

#[cfg(all(unix, feature = "events"))]
fn query_color_slot_raw(slot: u8) -> io::Result<Option<Color>> {
    send_query(slot)?;

    let filter = OscColorFilter { slot };
    loop {
        match internal::poll(Some(Duration::from_millis(2000)), &filter) {
            Ok(true) => match internal::read(&filter)? {
                InternalEvent::OscColor { payload, .. } => {
                    return Ok(match payload {
                        OscColorPayload::Rgb { r, g, b } => Some(Color::Rgb { r, g, b }),
                        OscColorPayload::Unrecognized(_) => None,
                    });
                }
                _ => continue,
            },
            Ok(false) => {
                return Err(io::Error::other(format!(
                    "The terminal did not report OSC color {} within a normal duration",
                    slot
                )));
            }
            Err(err) if err.kind() == io::ErrorKind::Interrupted => continue,
            Err(err) => return Err(err),
        }
    }
}

#[cfg(all(unix, feature = "events"))]
fn send_query(slot: u8) -> io::Result<()> {
    let sequence = format!("\x1B]{};?\x1B\\", slot);

    let sent = File::open("/dev/tty").and_then(|mut tty| {
        tty.write_all(sequence.as_bytes())?;
        tty.flush()
    });

    if sent.is_err() {
        let mut stdout = io::stdout();
        stdout.write_all(sequence.as_bytes())?;
        stdout.flush()?;
    }

    Ok(())
}

#[cfg(not(all(unix, feature = "events")))]
pub fn query_foreground_color() -> io::Result<Option<Color>> {
    Err(io::Error::new(
        io::ErrorKind::Unsupported,
        "query_foreground_color requires the \"events\" feature on Unix platforms",
    ))
}

#[cfg(not(all(unix, feature = "events")))]
pub fn query_background_color() -> io::Result<Option<Color>> {
    Err(io::Error::new(
        io::ErrorKind::Unsupported,
        "query_background_color requires the \"events\" feature on Unix platforms",
    ))
}
