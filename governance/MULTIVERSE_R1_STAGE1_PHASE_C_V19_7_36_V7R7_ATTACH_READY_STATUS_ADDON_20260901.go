package main

import (
	"bufio"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
	"syscall"
	"time"
)

const v7r7SecureStatusPath = "/workspaces/.codespaces/.persistedshare/multiverse-v36-v7r7-session-status.txt"
const v7r7UIControlPath = "/workspaces/multiverse-research/MULTIVERSE_PRELIVE_START_HERE.md"
const v7r7ChallengePrefix = "PHASE_C_V19_7_36_V7R6_SESSION_CHALLENGE "
const v7r7WaitingLine = "PHASE_C_V19_7_36_V7R6_WAITING_FOR_EXTERNAL_SESSION_BINDING"
const v7r7ArmedLine = "PHASE_C_V19_7_36_V7R7_ARMED"

func v7r7Hex(s string, n int) bool {
	if len(s) != n {
		return false
	}
	_, err := hex.DecodeString(s)
	return err == nil
}

func v7r7Name(s string) bool {
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

func v7r7Safe(line string) bool {
	if line == v7r7WaitingLine {
		return true
	}
	if !strings.HasPrefix(line, v7r7ChallengePrefix) {
		return false
	}
	parts := strings.Fields(strings.TrimPrefix(line, v7r7ChallengePrefix))
	if len(parts) != 3 || !strings.HasPrefix(parts[0], "codespace=") || !strings.HasPrefix(parts[1], "challenge=") || !strings.HasPrefix(parts[2], "image_identity_sha256=") {
		return false
	}
	return v7r7Name(strings.TrimPrefix(parts[0], "codespace=")) && v7r7Hex(strings.TrimPrefix(parts[1], "challenge="), 32) && v7r7Hex(strings.TrimPrefix(parts[2], "image_identity_sha256="), 64)
}

func v7r7WriteBoth(secure, ui *os.File, line string) error {
	if _, err := fmt.Fprintln(secure, line); err != nil {
		return err
	}
	if _, err := fmt.Fprintln(ui, line); err != nil {
		return err
	}
	if err := secure.Sync(); err != nil {
		return err
	}
	return ui.Sync()
}

func v7r7Fatal(original, secure, ui *os.File, code string) {
	if original != nil {
		fmt.Fprintln(original, "PHASE_C_V19_7_36_V7R7_STATUS_CHANNEL_DENIED:"+code)
	} else {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_STATUS_CHANNEL_DENIED:"+code)
	}
	if secure != nil {
		secure.Close()
	}
	if ui != nil {
		ui.Close()
	}
	os.Exit(92)
}

func v7r7MirrorUntilWaiting(r, w *os.File, originalFD int, secure, ui *os.File, done chan<- struct{}) {
	defer r.Close()
	if done != nil {
		defer close(done)
	}
	original := os.NewFile(uintptr(originalFD), "multiverse-original-stdout")
	if original == nil {
		v7r7Fatal(nil, secure, ui, "ORIGINAL_STDOUT")
	}
	defer original.Close()
	reader := bufio.NewReaderSize(r, 4096)
	challengeSeen := false
	for {
		line, err := reader.ReadString('\n')
		if len(line) > 8192 {
			v7r7Fatal(original, secure, ui, "STDOUT_LINE_TOO_LONG")
		}
		if line != "" {
			if _, werr := io.WriteString(original, line); werr != nil {
				v7r7Fatal(original, secure, ui, "ORIGINAL_STDOUT_WRITE")
			}
			trimmed := strings.TrimSuffix(strings.TrimSuffix(line, "\n"), "\r")
			if strings.HasPrefix(trimmed, v7r7ChallengePrefix) {
				if challengeSeen || !v7r7Safe(trimmed) {
					v7r7Fatal(original, secure, ui, "CHALLENGE_LINE")
				}
				if werr := v7r7WriteBoth(secure, ui, trimmed); werr != nil {
					v7r7Fatal(original, secure, ui, "CHALLENGE_WRITE")
				}
				challengeSeen = true
			}
			if trimmed == v7r7WaitingLine {
				if !challengeSeen {
					v7r7Fatal(original, secure, ui, "WAITING_BEFORE_CHALLENGE")
				}
				if werr := v7r7WriteBoth(secure, ui, trimmed); werr != nil {
					v7r7Fatal(original, secure, ui, "WAITING_WRITE")
				}
				if werr := syscall.Dup2(originalFD, int(os.Stdout.Fd())); werr != nil {
					v7r7Fatal(original, secure, ui, "STDOUT_RESTORE")
				}
				w.Close()
				secure.Close()
				ui.Close()
				return
			}
		}
		if err != nil {
			if err == io.EOF {
				secure.Close()
				ui.Close()
				return
			}
			v7r7Fatal(original, secure, ui, "STDOUT_READ")
		}
	}
}

func v7r7OpenChannels(ruid uint32) (*os.File, *os.File, error) {
	for _, p := range []string{"/workspaces", "/workspaces/.codespaces", "/workspaces/.codespaces/.persistedshare"} {
		st, err := os.Lstat(p)
		if err != nil || !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
			return nil, nil, fmt.Errorf("secure-parent:%s", p)
		}
	}
	secure, err := os.OpenFile(v7r7SecureStatusPath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0444)
	if err != nil {
		return nil, nil, err
	}
	if err := secure.Chown(0, 0); err != nil || secure.Chmod(0444) != nil {
		secure.Close()
		return nil, nil, fmt.Errorf("secure-owner-mode")
	}
	fd, err := syscall.Open(v7r7UIControlPath, syscall.O_WRONLY|syscall.O_TRUNC|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
	if err != nil {
		secure.Close()
		return nil, nil, err
	}
	ui := os.NewFile(uintptr(fd), "v7r7-ui-control")
	var st syscall.Stat_t
	if err := syscall.Fstat(fd, &st); err != nil || st.Uid != ruid || st.Mode&syscall.S_IFMT != syscall.S_IFREG || uint32(st.Mode)&0777 != 0644 {
		ui.Close()
		secure.Close()
		return nil, nil, fmt.Errorf("ui-control-class")
	}
	if err := ui.Chown(0, 0); err != nil || ui.Chmod(0444) != nil {
		ui.Close()
		secure.Close()
		return nil, nil, fmt.Errorf("ui-control-owner-mode")
	}
	for _, line := range []string{v7r7ArmedLine, "timer_state=STARTING_TRUSTED_GITHUB_SERVER_TIME", "runtime=OFF"} {
		if err := v7r7WriteBoth(secure, ui, line); err != nil {
			ui.Close()
			secure.Close()
			return nil, nil, err
		}
	}
	return secure, ui, nil
}

func v7r7Install() error {
	x := os.Getenv("MULTIVERSE_V7R7_ARM_RUID")
	n, err := strconv.ParseUint(x, 10, 32)
	if err != nil || n == 0 {
		return fmt.Errorf("arm-ruid")
	}
	secure, ui, err := v7r7OpenChannels(uint32(n))
	if err != nil {
		return err
	}
	originalFD, err := syscall.Dup(int(os.Stdout.Fd()))
	if err != nil {
		secure.Close(); ui.Close(); return err
	}
	r, w, err := os.Pipe()
	if err != nil {
		syscall.Close(originalFD); secure.Close(); ui.Close(); return err
	}
	if err := syscall.Dup2(int(w.Fd()), int(os.Stdout.Fd())); err != nil {
		r.Close(); w.Close(); syscall.Close(originalFD); secure.Close(); ui.Close(); return err
	}
	go v7r7MirrorUntilWaiting(r, w, originalFD, secure, ui, nil)
	return nil
}

func v7r7Selftest() {
	good := v7r7ChallengePrefix + "codespace=studious-halibut challenge=" + strings.Repeat("a", 32) + " image_identity_sha256=" + strings.Repeat("b", 64)
	if !v7r7Safe(good) || !v7r7Safe(v7r7WaitingLine) || v7r7Safe(good+" device_code=NO") || v7r7Safe("device code 1234-5678") {
		panic("v7r7-safe-lines")
	}
	td, err := os.MkdirTemp("", "multiverse-v7r7-status-")
	if err != nil { panic("temp") }
	defer os.RemoveAll(td)
	secure, _ := os.OpenFile(td+"/secure", os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	ui, _ := os.OpenFile(td+"/ui", os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	old, _ := syscall.Dup(int(os.Stdout.Fd()))
	captureR, captureW, _ := os.Pipe()
	sourceR, sourceW, _ := os.Pipe()
	_ = syscall.Dup2(int(sourceW.Fd()), int(os.Stdout.Fd()))
	done := make(chan struct{})
	go v7r7MirrorUntilWaiting(sourceR, sourceW, int(captureW.Fd()), secure, ui, done)
	fmt.Println(good)
	fmt.Println(v7r7WaitingLine)
	select { case <-done: case <-time.After(2*time.Second): panic("mirror-timeout") }
	const downstream = "DEVICE_CODE_SHOULD_REMAIN_TERMINAL_ONLY_AFTER_RESTORE"
	fmt.Println(downstream)
	_ = syscall.Dup2(old, int(os.Stdout.Fd())); syscall.Close(old); captureW.Close()
	captured, _ := io.ReadAll(captureR); captureR.Close()
	sb, _ := os.ReadFile(td+"/secure"); ub, _ := os.ReadFile(td+"/ui")
	if !strings.Contains(string(captured), downstream) || strings.Contains(string(sb), downstream) || strings.Contains(string(ub), downstream) || !strings.Contains(string(sb), good) || !strings.Contains(string(ub), v7r7WaitingLine) {
		panic("persistence-boundary")
	}
	fmt.Println("PHASE_C_V19_7_36_V7R7_ATTACH_READY_OBSERVABILITY_SELFTEST_PASS")
	fmt.Println("PHASE_C_V19_7_36_V7R7_ATTACH_READY_OBSERVABILITY_BEHAVIOR_SELFTEST_PASS")
}

func init() {
	if len(os.Args) == 2 && os.Args[1] == "build-selftest" {
		v7r7Selftest()
		return
	}
	if os.Getenv("CODESPACES") != "true" || os.Geteuid() != 0 {
		return
	}
	if err := v7r7Install(); err != nil {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_STATUS_CHANNEL_DENIED:"+err.Error())
		os.Exit(92)
	}
}
