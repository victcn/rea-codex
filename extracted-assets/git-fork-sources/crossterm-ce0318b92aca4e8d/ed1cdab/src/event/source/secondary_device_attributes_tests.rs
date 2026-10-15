//! Secondary device attributes must remain terminal input, including across startup replay.

use super::Parser;
use crate::event::{Event, InternalEvent, KeyCode};

#[test]
fn secondary_device_attributes_do_not_become_keys_at_any_split() {
    for reply in ["\x1b[>1;95;0c", "\x1b[>64;2500;0c", "\x1b[>1;4000;46c"] {
        let input = format!("a{reply}b");
        for split in 0..=input.len() {
            let mut parser = Parser::default();
            parser.buffer_external_input(&input.as_bytes()[..split]);
            parser.advance(&input.as_bytes()[split..], /*more*/ false);
            assert_eq!(
                parser.collect::<Vec<_>>(),
                vec![
                    InternalEvent::Event(Event::Key(KeyCode::Char('a').into())),
                    InternalEvent::Event(Event::Key(KeyCode::Char('b').into())),
                ],
                "reply {reply:?}, split {split}"
            );
        }
    }
}

#[test]
#[cfg(feature = "bracketed-paste")]
fn secondary_device_attributes_inside_paste_remain_text() {
    let mut parser = Parser::default();
    parser.advance(b"\x1b[200~\x1b[>1;95;0c\x1b[201~", /*more*/ false);
    assert_eq!(
        parser.collect::<Vec<_>>(),
        vec![InternalEvent::Event(Event::Paste("\x1b[>1;95;0c".into()))]
    );
}
