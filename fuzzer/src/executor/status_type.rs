use crate::byte_count::{UdpByteCount, AmpByteCount};
use crate::branches::PathV;

#[derive(Debug, Clone, PartialEq)]
pub enum StatusType {
    Normal,
    Timeout,
    Crash,
    Skip,
    Error,
    Amp(PathV, AmpByteCount),
}
