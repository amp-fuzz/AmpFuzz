use std::thread::JoinHandle;
use std::net::UdpSocket;
use std::thread;
use std::fs::File;
use byteorder::WriteBytesExt;
use super::nix::sys::select::{FdSet, FD_SETSIZE};
use super::nix::Error;
use std::os::unix::io::{FromRawFd, AsRawFd, RawFd};
use std::ops;
use std::ops::Add;
use crate::byte_count::UdpByteCount;

lazy_static! {
    static ref PIPE:(RawFd,RawFd) = nix::unistd::pipe2(nix::fcntl::OFlag::O_NONBLOCK).expect("Error creating pipe");
}


pub struct RecvThread {
    write_fd: RawFd,
    receiver: JoinHandle<UdpByteCount>,
}

impl RecvThread {
    pub fn new(socket: UdpSocket) -> Self {
        let receiver = thread::spawn(move || { listen_for_udp(socket, PIPE.0) });
        Self {
            write_fd: PIPE.1,
            receiver,
        }
    }

    pub fn stop(mut self) -> UdpByteCount {
        let buf = [0; 1];
        nix::unistd::write(self.write_fd, &buf);
        return self.receiver.join().expect("Error joining udp receiver thread");
    }
}

fn listen_for_udp(udp_socket: UdpSocket, read_fd: RawFd) -> UdpByteCount {
    let mut bytes_received = UdpByteCount::default();
    udp_socket.set_nonblocking(true);

    /*   if read_fd as usize >= FD_SETSIZE {
           panic!("read_fd too big");
       }
       println!("read_fd: {:?}", read_fd);
   */
    loop {
        let mut read_fds = FdSet::new();
        read_fds.insert(udp_socket.as_raw_fd());
        read_fds.insert(read_fd);

        match nix::sys::select::pselect(None, Some(&mut read_fds), None, None, None, None) {
            Ok(_) => {
                if read_fds.contains(udp_socket.as_raw_fd()) {
                    bytes_received += drain_udp_socket(&udp_socket);
                }
                if read_fds.contains(read_fd) {
                    drain(read_fd);
                    break;
                }
            }
            Err(_) => { break; }
        }
    }
    bytes_received += drain_udp_socket(&udp_socket);
    bytes_received
}

fn drain_udp_socket(udp_socket: &UdpSocket) -> UdpByteCount {
    let mut bytes_received = UdpByteCount::default();
    let mut buf = [0; 65536];
    loop {
        match udp_socket.recv(&mut buf) {
            Ok(n) => {
                bytes_received += n;
            }
            Err(_) => { break; }
        }
    }
    bytes_received
}

fn drain(fd: RawFd) {
    let mut buf = [0; 8192];
    loop {
        match nix::unistd::read(fd, &mut buf) {
            Ok(n) => {}
            Err(_) => { break; }
        }
    }
}