use std::ops;
use std::cmp::{Ordering, max};

use serde::{Serialize, Deserialize};
use std::slice::Iter;
use std::iter::Map;

pub static UDP_HEADER_SIZE: usize = 8;
pub static IPv4_HEADER_SIZE: usize = 20;
pub static ETH_HEADER_SIZE: usize = 6 + 6 + 2 + 4;
pub static MIN_ETH_FRAME_SIZE: usize = 64;

#[derive(Debug, Default, Clone, PartialOrd, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpByteCount {
    pub l7: Vec<usize>,
}

impl UdpByteCount {
    pub fn from_l7(l7_size: usize) -> Self {
        Self {
            l7: vec![l7_size]
        }
    }

    fn as_l7_iter<'a>(&'a self) -> Iter<'a, usize> {
        return self.l7.iter();
    }

    fn as_l4_iter<'a>(&'a self) -> Map<Iter<'a, usize>, fn(&'a usize) -> usize> {
        return self.as_l7_iter().map(|l7| l7 + UDP_HEADER_SIZE);
    }

    fn as_l3_iter<'a>(&'a self) -> Map<Map<Iter<'a, usize>, fn(&'a usize) -> usize>, fn(usize) -> usize> {
        return self.as_l4_iter().map(|l4| l4 + IPv4_HEADER_SIZE);
    }

    fn as_l2_iter<'a>(&'a self) -> Map<Map<Map<Iter<'a, usize>, fn(&'a usize) -> usize>, fn(usize) -> usize>, fn(usize) -> usize> {
        return self.as_l3_iter().map(|l3| max(l3 + ETH_HEADER_SIZE, MIN_ETH_FRAME_SIZE));
    }

    pub fn l7_size(&self) -> usize {
        self.as_l7_iter().sum()
    }

    pub fn l4_size(&self) -> usize {
        self.as_l4_iter().sum()
    }

    pub fn l3_size(&self) -> usize {
        self.as_l3_iter().sum()
    }

    pub fn l2_size(&self) -> usize {
        self.as_l2_iter().sum()
    }
}

impl ops::Add<UdpByteCount> for UdpByteCount {
    type Output = UdpByteCount;

    fn add(self, rhs: UdpByteCount) -> Self::Output {
        let mut l7 = self.l7.clone();
        l7.extend(rhs.l7);
        UdpByteCount {
            l7
        }
    }
}

impl ops::AddAssign<UdpByteCount> for UdpByteCount {
    fn add_assign(&mut self, rhs: UdpByteCount) {
        self.l7.extend(rhs.l7)
    }
}

impl ops::Add<usize> for UdpByteCount {
    type Output = UdpByteCount;

    fn add(self, rhs: usize) -> Self::Output {
        let mut l7 = self.l7.clone();
        l7.push(rhs);
        UdpByteCount {
            l7
        }
    }
}

impl ops::AddAssign<usize> for UdpByteCount {
    fn add_assign(&mut self, rhs: usize) {
        self.l7.push(rhs);
    }
}

impl From<&UdpByteCount> for usize {
    fn from(x: &UdpByteCount) -> Self {
        x.l2_size()
    }
}


impl PartialEq<usize> for UdpByteCount {
    fn eq(&self, other: &usize) -> bool {
        usize::from(self) == *other
    }
}

impl PartialOrd<usize> for UdpByteCount {
    fn partial_cmp(&self, other: &usize) -> Option<Ordering> {
        Option::from(usize::from(self).cmp(other))
    }
}

#[derive(Debug, Default, Clone, PartialEq, Eq, PartialOrd, Serialize, Deserialize)]
pub struct AmpByteCount {
    pub bytes_in: UdpByteCount,
    pub bytes_out: UdpByteCount,
}

impl AmpByteCount {
    pub fn as_factor(&self) -> f64 {
        if self.bytes_in > 0 {
            (usize::from(&self.bytes_out) as f64) / (usize::from(&self.bytes_in) as f64)
        } else {
            0.0
        }
    }
}

impl Ord for AmpByteCount {
    fn cmp(&self, other: &Self) -> Ordering {
        let self_bytes_in = usize::from(&self.bytes_in);
        let self_bytes_out = usize::from(&self.bytes_out);
        let other_bytes_in = usize::from(&other.bytes_in);
        let other_bytes_out = usize::from(&other.bytes_out);
        if self_bytes_in > 0 && other_bytes_in > 0 {
            (self_bytes_out * other_bytes_in).cmp(&(other_bytes_out * self_bytes_in))
        } else {
            self_bytes_out.cmp(&other_bytes_out)
        }
    }
}