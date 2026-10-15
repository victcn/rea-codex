//! Regression coverage for characters delivered through Windows console input records.

use super::*;
use crossterm_winapi::InputRecord;
use winapi::um::wincon::{INPUT_RECORD, KEY_EVENT};

#[test]
fn preserves_escape_and_literal_characters_from_console_records() {
    for (virtual_key_code, character, code) in [
        (0, '\u{1b}', KeyCode::Esc),
        (VK_ESCAPE as u16, '\u{1b}', KeyCode::Esc),
        (0, '[', KeyCode::Char('[')),
        (0, '1', KeyCode::Char('1')),
        (0, '3', KeyCode::Char('3')),
        (0, ';', KeyCode::Char(';')),
        (0, '2', KeyCode::Char('2')),
        (0, 'u', KeyCode::Char('u')),
    ] {
        for (key_down, kind) in [(1, KeyEventKind::Press), (0, KeyEventKind::Release)] {
            for (control_key_state, modifiers) in [
                (0, KeyModifiers::NONE),
                (SHIFT_PRESSED, KeyModifiers::SHIFT),
            ] {
                // INPUT_RECORD contains only integers and unions of integer records.
                let mut record: INPUT_RECORD = unsafe { std::mem::zeroed() };
                record.EventType = KEY_EVENT;
                // Select the KEY_EVENT union member before conversion by crossterm_winapi.
                unsafe {
                    let key = record.Event.KeyEvent_mut();
                    key.bKeyDown = key_down;
                    key.wRepeatCount = 1;
                    key.wVirtualKeyCode = virtual_key_code;
                    *key.uChar.UnicodeChar_mut() = character as u16;
                    key.dwControlKeyState = control_key_state;
                }
                let InputRecord::KeyEvent(key) = InputRecord::from(record) else {
                    panic!("expected a key input record");
                };
                let mut surrogate_buffer = None;
                assert_eq!(
                    handle_key_event(key, &mut surrogate_buffer),
                    Some(Event::Key(KeyEvent::new_with_kind(code, modifiers, kind))),
                    "virtual key {virtual_key_code}, character {character:?}"
                );
            }
        }
    }
}
