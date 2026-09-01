package main

import (
	"fmt"
	"net"
	"os"
	"syscall"
	"time"
)

func die(s string) { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7_TRIGGER_DENIED:"+s); os.Exit(92) }
func main() {
	cap := os.NewFile(4, "cap")
	lf := os.NewFile(5, "wake-listener")
	if cap == nil || lf == nil { die("FDS") }
	defer cap.Close(); defer lf.Close()
	_, _, errno := syscall.RawSyscall6(syscall.SYS_PRCTL, 4, 0, 0, 0, 0, 0); if errno != 0 { die("DUMPABLE") }
	_, _, errno = syscall.RawSyscall6(syscall.SYS_PRCTL, 38, 1, 0, 0, 0, 0); if errno != 0 { die("NO_NEW_PRIVS") }
	l, e := net.FileListener(lf); if e != nil { die("LISTENER") }; defer l.Close()
	_ = l.(*net.UnixListener).SetDeadline(time.Now().Add(10 * time.Minute))
	c, e := l.Accept(); if e != nil { die("WAKE") }; defer c.Close()
	u := c.(*net.UnixConn); raw, _ := u.SyscallConn(); var peer *syscall.Ucred
	raw.Control(func(fd uintptr) { peer, _ = syscall.GetsockoptUcred(int(fd), syscall.SOL_SOCKET, syscall.SO_PEERCRED) })
	if peer == nil || peer.Uid != 1000 { die("WAKE_PEER") }
	b := make([]byte, 5); _ = c.SetReadDeadline(time.Now().Add(2 * time.Second)); n, e := c.Read(b)
	if e != nil || n != 5 || string(b) != "WAKE\n" { die("PROTOCOL") }
	if n, e = cap.Write([]byte{0x76}); e != nil || n != 1 { die("CAP_WRITE") }
	_ = cap.Sync(); fmt.Fprintln(c, "REVIEW_TRIGGER_ACCEPTED")
}
