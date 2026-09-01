package main

import (
	"bufio"
	"fmt"
	"net"
	"os"
	"time"
)

func main() {
	c, e := net.DialTimeout("unix", "/run/multiverse-v36-wake-v7.sock", 2*time.Second)
	if e != nil { os.Exit(92) }
	defer c.Close()
	if _, e = c.Write([]byte("WAKE\n")); e != nil { os.Exit(92) }
	_ = c.SetReadDeadline(time.Now().Add(3 * time.Second))
	s, e := bufio.NewReader(c).ReadString('\n')
	if e != nil || s != "REVIEW_TRIGGER_ACCEPTED\n" { os.Exit(92) }
	fmt.Print(s)
}
