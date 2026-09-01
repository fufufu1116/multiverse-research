package main

import (
	"bufio"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

const iphoneStatusDir = "/workspaces/.codespaces/.persistedshare"
const iphoneStatusPath = "/workspaces/.codespaces/.persistedshare/multiverse-v36-v7r6-session-status.txt"
const iphoneReadyLine = "PHASE_C_V19_7_36_V7R6_IPHONE_STATUS_CHANNEL_READY"
const iphoneChallengePrefix = "PHASE_C_V19_7_36_V7R6_SESSION_CHALLENGE "
const iphoneWaitingLine = "PHASE_C_V19_7_36_V7R6_WAITING_FOR_EXTERNAL_SESSION_BINDING"

func iphoneHex(s string, n int) bool {
	if len(s) != n {
		return false
	}
	_, err := hex.DecodeString(s)
	return err == nil
}

func iphoneCodespaceName(s string) bool {
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

func iphoneSafeStatusLine(line string) bool {
	if line == iphoneWaitingLine {
		return true
	}
	if !strings.HasPrefix(line, iphoneChallengePrefix) {
		return false
	}
	parts := strings.Fields(strings.TrimPrefix(line, iphoneChallengePrefix))
	if len(parts) != 3 {
		return false
	}
	if !strings.HasPrefix(parts[0], "codespace=") || !strings.HasPrefix(parts[1], "challenge=") || !strings.HasPrefix(parts[2], "image_identity_sha256=") {
		return false
	}
	name := strings.TrimPrefix(parts[0], "codespace=")
	challenge := strings.TrimPrefix(parts[1], "challenge=")
	identity := strings.TrimPrefix(parts[2], "image_identity_sha256=")
	return iphoneCodespaceName(name) && iphoneHex(challenge, 32) && iphoneHex(identity, 64)
}

func iphoneMirrorUntilWaiting(r, w *os.File, originalFD int, status *os.File, done chan<- struct{}) {
	defer r.Close()
	if done != nil {
		defer close(done)
	}
	original := os.NewFile(uintptr(originalFD), "multiverse-original-stdout")
	if original == nil {
		iphoneFatal(nil, status, "ORIGINAL_STDOUT")
	}
	defer original.Close()
	reader := bufio.NewReaderSize(r, 4096)
	challengeSeen := false
	for {
		line, err := reader.ReadString('\n')
		if len(line) > 8192 {
			iphoneFatal(original, status, "STDOUT_LINE_TOO_LONG")
		}
		if line != "" {
			if _, werr := io.WriteString(original, line); werr != nil {
				iphoneFatal(original, status, "ORIGINAL_STDOUT_WRITE")
			}
			trimmed := strings.TrimSuffix(strings.TrimSuffix(line, "\n"), "\r")
			if strings.HasPrefix(trimmed, iphoneChallengePrefix) {
				if challengeSeen || !iphoneSafeStatusLine(trimmed) {
					iphoneFatal(original, status, "CHALLENGE_LINE")
				}
				if _, werr := fmt.Fprintln(status, trimmed); werr != nil {
					iphoneFatal(original, status, "STATUS_CHALLENGE_WRITE")
				}
				if werr := status.Sync(); werr != nil {
					iphoneFatal(original, status, "STATUS_CHALLENGE_SYNC")
				}
				challengeSeen = true
			}
			if trimmed == iphoneWaitingLine {
				if !challengeSeen {
					iphoneFatal(original, status, "WAITING_BEFORE_CHALLENGE")
				}
				if _, werr := fmt.Fprintln(status, trimmed); werr != nil {
					iphoneFatal(original, status, "STATUS_WAITING_WRITE")
				}
				if werr := status.Sync(); werr != nil {
					iphoneFatal(original, status, "STATUS_WAITING_SYNC")
				}
				if werr := syscall.Dup2(originalFD, int(os.Stdout.Fd())); werr != nil {
					iphoneFatal(original, status, "STDOUT_RESTORE")
				}
				w.Close()
				status.Close()
				return
			}
		}
		if err != nil {
			if err == io.EOF {
				status.Close()
				return
			}
			iphoneFatal(original, status, "STDOUT_READ")
		}
	}
}

func iphoneSelftest() {
	good := iphoneChallengePrefix + "codespace=studious-halibut challenge=" + strings.Repeat("a", 32) + " image_identity_sha256=" + strings.Repeat("b", 64)
	if !iphoneSafeStatusLine(good) || !iphoneSafeStatusLine(iphoneWaitingLine) {
		panic("iphone-observability-positive")
	}
	bad := []string{
		good + " device_code=SHOULD_NEVER_PERSIST",
		iphoneChallengePrefix + "codespace=bad/name challenge=" + strings.Repeat("a", 32) + " image_identity_sha256=" + strings.Repeat("b", 64),
		iphoneChallengePrefix + "codespace=studious-halibut challenge=" + strings.Repeat("a", 31) + " image_identity_sha256=" + strings.Repeat("b", 64),
		"device code 1234-5678",
		"Logged in to github.com",
	}
	for i, line := range bad {
		if iphoneSafeStatusLine(line) {
			panic(fmt.Sprintf("iphone-observability-negative-%d", i))
		}
	}

	td, err := os.MkdirTemp("", "multiverse-iphone-observability-")
	if err != nil {
		panic("iphone-observability-tempdir")
	}
	defer os.RemoveAll(td)
	exclusivePath := filepath.Join(td, "exclusive-status.txt")
	f, err := os.OpenFile(exclusivePath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0444)
	if err != nil {
		panic("iphone-observability-exclusive-create")
	}
	f.Close()
	if second, err := os.OpenFile(exclusivePath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0444); err == nil {
		second.Close()
		panic("iphone-observability-exclusive-recreate-accepted")
	}

	statusPath := filepath.Join(td, "behavior-status.txt")
	status, err := os.OpenFile(statusPath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		panic("iphone-observability-behavior-status")
	}
	if _, err := fmt.Fprintln(status, iphoneReadyLine); err != nil {
		panic("iphone-observability-behavior-ready")
	}
	oldStdout, err := syscall.Dup(int(os.Stdout.Fd()))
	if err != nil {
		panic("iphone-observability-behavior-old-stdout")
	}
	defer syscall.Close(oldStdout)
	captureR, captureW, err := os.Pipe()
	if err != nil {
		panic("iphone-observability-behavior-capture-pipe")
	}
	sourceR, sourceW, err := os.Pipe()
	if err != nil {
		panic("iphone-observability-behavior-source-pipe")
	}
	if err := syscall.Dup2(int(sourceW.Fd()), int(os.Stdout.Fd())); err != nil {
		panic("iphone-observability-behavior-redirect")
	}
	done := make(chan struct{})
	go iphoneMirrorUntilWaiting(sourceR, sourceW, int(captureW.Fd()), status, done)
	fmt.Println(good)
	fmt.Println(iphoneWaitingLine)
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		panic("iphone-observability-behavior-timeout")
	}
	const downstream = "DEVICE_CODE_SHOULD_REMAIN_TERMINAL_ONLY_AFTER_RESTORE"
	fmt.Println(downstream)
	if err := syscall.Dup2(oldStdout, int(os.Stdout.Fd())); err != nil {
		panic("iphone-observability-behavior-final-restore")
	}
	captureW.Close()
	captured, err := io.ReadAll(captureR)
	captureR.Close()
	if err != nil {
		panic("iphone-observability-behavior-capture-read")
	}
	statusBytes, err := os.ReadFile(statusPath)
	if err != nil {
		panic("iphone-observability-behavior-status-read")
	}
	captureText := string(captured)
	statusText := string(statusBytes)
	if !strings.Contains(captureText, good) || !strings.Contains(captureText, iphoneWaitingLine) || !strings.Contains(captureText, downstream) {
		panic("iphone-observability-behavior-original-stream")
	}
	if !strings.Contains(statusText, iphoneReadyLine) || !strings.Contains(statusText, good) || !strings.Contains(statusText, iphoneWaitingLine) || strings.Contains(statusText, downstream) {
		panic("iphone-observability-behavior-persistence-boundary")
	}
	fmt.Println("PHASE_C_V19_7_36_V7R6_IPHONE_OBSERVABILITY_SELFTEST_PASS")
	fmt.Println("PHASE_C_V19_7_36_V7R6_IPHONE_OBSERVABILITY_BEHAVIOR_SELFTEST_PASS")
}

func iphoneOpenStatus() (*os.File, error) {
	for _, p := range []string{"/workspaces", "/workspaces/.codespaces", iphoneStatusDir} {
		st, err := os.Lstat(p)
		if err != nil {
			return nil, fmt.Errorf("status-parent:%s:%w", p, err)
		}
		if !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
			return nil, fmt.Errorf("status-parent-class:%s", p)
		}
	}
	f, err := os.OpenFile(iphoneStatusPath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0444)
	if err != nil {
		return nil, err
	}
	if err := os.Chown(iphoneStatusPath, 0, 0); err != nil {
		f.Close()
		return nil, err
	}
	if err := os.Chmod(iphoneStatusPath, 0444); err != nil {
		f.Close()
		return nil, err
	}
	if _, err := fmt.Fprintln(f, iphoneReadyLine); err != nil {
		f.Close()
		return nil, err
	}
	if err := f.Sync(); err != nil {
		f.Close()
		return nil, err
	}
	return f, nil
}

func iphoneFatal(original *os.File, status *os.File, msg string) {
	if original != nil {
		fmt.Fprintln(original, "PHASE_C_V19_7_36_V7R6_IPHONE_STATUS_CHANNEL_DENIED:"+msg)
	} else {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R6_IPHONE_STATUS_CHANNEL_DENIED:"+msg)
	}
	if status != nil {
		status.Close()
	}
	os.Exit(92)
}

func iphoneInstallStatusChannel() error {
	status, err := iphoneOpenStatus()
	if err != nil {
		return err
	}
	originalFD, err := syscall.Dup(int(os.Stdout.Fd()))
	if err != nil {
		status.Close()
		return err
	}
	r, w, err := os.Pipe()
	if err != nil {
		syscall.Close(originalFD)
		status.Close()
		return err
	}
	if err := syscall.Dup2(int(w.Fd()), int(os.Stdout.Fd())); err != nil {
		r.Close()
		w.Close()
		syscall.Close(originalFD)
		status.Close()
		return err
	}
	go iphoneMirrorUntilWaiting(r, w, originalFD, status, nil)
	return nil
}

func init() {
	if len(os.Args) == 2 && os.Args[1] == "build-selftest" {
		iphoneSelftest()
		return
	}
	if os.Getenv("CODESPACES") != "true" || os.Geteuid() != 0 {
		return
	}
	if err := iphoneInstallStatusChannel(); err != nil {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R6_IPHONE_STATUS_CHANNEL_DENIED:"+err.Error())
		os.Exit(92)
	}
}
