package main

import (
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"strings"
	"syscall"
)

const uiControlPath = "/workspaces/multiverse-research/MULTIVERSE_PRELIVE_START_HERE.md"
const uiReadyPath = "/workspaces/.codespaces/.persistedshare/multiverse-v36-v7r7-ui-ready.txt"
const uiSessionPath = "/workspaces/.codespaces/.persistedshare/multiverse-v36-v7r7-session-status.txt"
const armLockPath = "/run/multiverse-v36-v7r7-arm.lock"
const armCommand = "/usr/local/bin/multiverse-v36-arm-v7r7"

func validName(s string) bool {
	if len(s) == 0 || len(s) > 128 {
		return false
	}
	for _, r := range s {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' || r == '-' {
			continue
		}
		return false
	}
	return true
}

func exactReady(name string) string {
	return "PHASE_C_V19_7_36_V7R7_UI_READY\n" +
		"codespace=" + name + "\n" +
		"timer_state=NOT_STARTED\n" +
		"arm_state=NOT_STARTED\n" +
		"arm_command=" + armCommand + "\n" +
		"next_action=RETURN_TO_CORE_BEFORE_ARM\n" +
		"runtime=OFF\n"
}

func controlReady(name string) string {
	return "# MULTIVERSE PRE-LIVE CONTROL — V19.7.36 v7r7\n\n" +
		"`PHASE_C_V19_7_36_V7R7_UI_READY`\n\n" +
		"- codespace=`" + name + "`\n" +
		"- timer_state=`NOT_STARTED`\n" +
		"- arm_state=`NOT_STARTED`\n" +
		"- next_action=`RETURN_TO_CORE_BEFORE_ARM`\n" +
		"- runtime=`OFF`\n\n" +
		"The strict 600-second challenge window has not started. Do not run the arm command until Core Fresh-rebinds this Codespace and explicitly says to arm.\n\n" +
		"Reviewed arm command (do not run yet): `" + armCommand + "`\n"
}

func writeNoFollow(path, body string, uid uint32) error {
	fd, err := syscall.Open(path, syscall.O_WRONLY|syscall.O_TRUNC|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
	if err != nil {
		return err
	}
	f := os.NewFile(uintptr(fd), path)
	defer f.Close()
	var st syscall.Stat_t
	if err := syscall.Fstat(fd, &st); err != nil {
		return err
	}
	if st.Uid != uid || st.Mode&syscall.S_IFMT != syscall.S_IFREG || st.Mode&0022 != 0 {
		return fmt.Errorf("control-class")
	}
	if _, err := io.WriteString(f, body); err != nil {
		return err
	}
	return f.Sync()
}

func main() {
	if len(os.Args) != 1 {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:ARGS")
		os.Exit(92)
	}
	if os.Geteuid() == 0 {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:ROOT_REMOTE_USER")
		os.Exit(92)
	}
	if os.Getenv("CODESPACES") != "true" {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:CODESPACES")
		os.Exit(92)
	}
	name := os.Getenv("CODESPACE_NAME")
	if !validName(name) {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:CODESPACE_NAME")
		os.Exit(92)
	}
	_ = hex.EncodeToString([]byte(name)) // force deterministic pure-Go encoding closure; no authority semantics.
	if _, err := os.Lstat(armLockPath); err == nil {
		fmt.Println("PHASE_C_V19_7_36_V7R7_UI_READY_ARM_ALREADY_STARTED_NO_REWRITE")
		return
	} else if !os.IsNotExist(err) {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:ARM_LOCK_STAT")
		os.Exit(92)
	}
	if _, err := os.Lstat(uiSessionPath); err == nil {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:SESSION_STATUS_PREEXISTS")
		os.Exit(92)
	} else if !os.IsNotExist(err) {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:SESSION_STATUS_STAT")
		os.Exit(92)
	}
	ready := exactReady(name)
	f, err := os.OpenFile(uiReadyPath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0444)
	if err != nil {
		if !os.IsExist(err) {
			fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:READY_CREATE")
			os.Exit(92)
		}
		b, rerr := os.ReadFile(uiReadyPath)
		if rerr != nil || string(b) != ready {
			fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:READY_STALE_OR_AMBIGUOUS")
			os.Exit(92)
		}
	} else {
		if _, err := io.WriteString(f, ready); err != nil || f.Sync() != nil || f.Close() != nil {
			fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:READY_WRITE")
			os.Exit(92)
		}
		_ = os.Chmod(uiReadyPath, 0444)
	}
	if err := writeNoFollow(uiControlPath, controlReady(name), uint32(os.Geteuid())); err != nil {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:CONTROL_WRITE:"+strings.ReplaceAll(err.Error(), "\n", "_"))
		os.Exit(92)
	}
	fmt.Println("PHASE_C_V19_7_36_V7R7_UI_READY_WRITER_PASS timer_state=NOT_STARTED runtime=OFF")
}
