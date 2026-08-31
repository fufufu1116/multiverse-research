package main

import (
	"bufio"
	"fmt"
	"net"
	"os"
	"syscall"
	"time"
)

const sock = "/run/multiverse-v36-anchor.sock"

func main() {
	c, e := net.DialTimeout("unix", sock, 2*time.Second)
	if e != nil {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V6_TRIGGER_DENIED:CONNECT")
		os.Exit(92)
	}
	defer c.Close()
	uc, ok := c.(*net.UnixConn)
	if !ok {
		os.Exit(92)
	}
	raw, e := uc.SyscallConn()
	if e != nil {
		os.Exit(92)
	}
	var pe error
	raw.Control(func(fd uintptr) {
		u, er := syscall.GetsockoptUcred(int(fd), syscall.SOL_SOCKET, syscall.SO_PEERCRED)
		pe = er
		if pe == nil && u.Uid != 0 {
			pe = fmt.Errorf("producer uid")
		}
	})
	if pe != nil {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V6_TRIGGER_DENIED:PEER")
		os.Exit(92)
	}
	if _, e = c.Write([]byte("START V19.7.36-v6\n")); e != nil {
		os.Exit(92)
	}
	_ = c.SetReadDeadline(time.Now().Add(30 * time.Second))
	s, e := bufio.NewReader(c).ReadString('\n')
	if e != nil {
		os.Exit(92)
	}
	fmt.Print(s)
	if s != "REVIEW_FREEZE_RC92_CONFIRMED\n" {
		os.Exit(92)
	}
}
