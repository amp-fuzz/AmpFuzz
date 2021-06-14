use crate::{shm, defs};
use std::{env, process};
use std::time::{Instant, UNIX_EPOCH, Duration, SystemTime};
use std::io::Error;
use std::ops::Add;

#[derive(Debug)]
pub struct ShmListenSemaphore {
    pub semaphore: shm::SHM<libc::sem_t>,
}

// just assume we can share the libc::sem_t between threads...
// in practice this should just mean passing a pointer, so I guess it's fine?
unsafe impl Send for ShmListenSemaphore {}

impl ShmListenSemaphore {
    pub fn new() -> Self {
        let semaphore = shm::SHM::<libc::sem_t>::new();

        unsafe { libc::sem_init(semaphore.get_ptr(), 1, 0); }

        Self {
            semaphore
        }
    }

    pub fn from_id(id: i32) -> Self {
        let mut semaphore = shm::SHM::<libc::sem_t>::from_id(id);
        Self {
            semaphore
        }
    }

    pub fn get_from_env_id() -> Option<Self> {
        let id_val = env::var(defs::LISTEN_SEM_ENV_VAR);
        match id_val {
            Ok(val) => {
                let shm_id = val.parse::<i32>().expect("Could not parse i32 value.");
                let semaphore = shm::SHM::<libc::sem_t>::from_id(shm_id);
                if semaphore.is_fail() {
                    process::exit(1);
                }
                Some(Self { semaphore })
            }
            Err(_) => None,
        }
    }

    #[inline(always)]
    pub fn get_id(&self) -> i32 {
        self.semaphore.get_id()
    }

    pub fn wait(&self) -> bool {
        debug!("waiting for semaphore...");
        let ret = unsafe { libc::sem_wait(self.semaphore.get_ptr()) };
        if ret < 0 {
            error!("semaphore error: {}", Error::last_os_error());
        }
        ret == 0
    }

    pub fn try_wait(&self) -> bool {
        debug!("waiting for semaphore...");
        let ret = unsafe { libc::sem_trywait(self.semaphore.get_ptr()) };
        if ret < 0 {
            debug!("semaphore error: {}", Error::last_os_error());
        }
        ret == 0
    }

    pub fn drain(&self) {
        while self.try_wait() {}
    }

    pub fn wait_timeout(&self, timeout: &Duration) -> bool {
        let timeout = SystemTime::now().add(*timeout).duration_since(UNIX_EPOCH).expect("Failed to compute timeout");
        let mut timeout_ts = libc::timespec {
            tv_sec: timeout.as_secs() as libc::time_t,
            tv_nsec: timeout.subsec_nanos() as libc::c_long,
        };
        debug!("waiting for semaphore with timeout of s={}, ns={}", timeout_ts.tv_sec, timeout_ts.tv_nsec);
        let ret = unsafe { libc::sem_timedwait(self.semaphore.get_ptr(), &timeout_ts) };
        debug!("sem_timedwait returned {}", ret);
        if ret < 0 {
            error!("semaphore error: {}", Error::last_os_error());
        }
        ret == 0
    }

    pub fn post(&self) -> bool {
        debug!("posting semaphore!");
        let ret = unsafe { libc::sem_post(self.semaphore.get_ptr()) };
        if ret < 0 {
            error!("semaphore error: {}", Error::last_os_error());
        }
        ret == 0
    }
}