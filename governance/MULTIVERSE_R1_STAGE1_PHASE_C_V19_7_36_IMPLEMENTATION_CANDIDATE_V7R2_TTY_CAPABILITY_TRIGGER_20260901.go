package main

import (
    "bufio"
    "fmt"
    "os"
    "strings"
    "syscall"
    "unsafe"
)

func die(s string) { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R2_TRIGGER_DENIED:"+s); os.Exit(92) }

func rootImmutableText(path string) string {
    f, err := os.Open(path); if err != nil { die("TTY_POLICY_OPEN") }; defer f.Close()
    st, err := f.Stat(); if err != nil { die("TTY_POLICY_STAT") }
    if st.Sys().(*syscall.Stat_t).Uid != 0 || st.Mode().Perm()&0022 != 0 || !st.Mode().IsRegular() { die("TTY_POLICY_CLASS_C") }
    b := make([]byte, 64); n, _ := f.Read(b); return strings.TrimSpace(string(b[:n]))
}

func main() {
    if os.Geteuid() == 1000 { die("DEDICATED_UID_REQUIRED") }
    capf := os.NewFile(4, "one-shot-capability")
    if capf == nil { die("CAP_FD") }
    defer capf.Close()
    if _, _, e := syscall.RawSyscall6(syscall.SYS_PRCTL, 4, 0, 0, 0, 0, 0); e != 0 { die("DUMPABLE") }
    if _, _, e := syscall.RawSyscall6(syscall.SYS_PRCTL, 38, 1, 0, 0, 0, 0); e != 0 { die("NO_NEW_PRIVS") }
    if rootImmutableText("/proc/sys/dev/tty/legacy_tiocsti") != "0" { die("TIOCSTI_POLICY") }
    var term syscall.Termios
    if _, _, e := syscall.Syscall(syscall.SYS_IOCTL, os.Stdin.Fd(), uintptr(syscall.TCGETS), uintptr(unsafe.Pointer(&term))); e != 0 { die("STDIN_NOT_TTY") }
    fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R2_OWNER_ENTER_READY")
    r := bufio.NewReaderSize(os.Stdin, 8)
    b, err := r.ReadByte(); if err != nil || b != '\n' { die("OWNER_ACTION") }
    if r.Buffered() != 0 { die("EXTRA_INPUT") }
    n, err := capf.Write([]byte{0x72}); if err != nil || n != 1 { die("CAPABILITY_DISCHARGE") }
    fmt.Println("PHASE_C_V19_7_36_V7R2_OWNER_ENTER_ACCEPTED")
}
