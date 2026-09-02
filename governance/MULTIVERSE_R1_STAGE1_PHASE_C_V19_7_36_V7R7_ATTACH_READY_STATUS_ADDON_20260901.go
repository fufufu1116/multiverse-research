package main

import (
	"bufio"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"
)

const v7r7SecureStatusDir = "/run/multiverse-v36-v7r7"
const v7r7SecureStatusPath = v7r7SecureStatusDir + "/session-status.txt"
const v7r7UIControlLeaf = "MULTIVERSE_PRELIVE_START_HERE.md"
const v7r7ChallengePrefix = "PHASE_C_V19_7_36_V7R6_SESSION_CHALLENGE "
const v7r7WaitingLine = "PHASE_C_V19_7_36_V7R6_WAITING_FOR_EXTERNAL_SESSION_BINDING"
const v7r7ArmedLine = "PHASE_C_V19_7_36_V7R7_ARMED"
const v7r7FailedClosedLine = "gate_state=FAILED_CLOSED"

func v7r7Hex(s string, n int) bool {
	if len(s) != n { return false }
	_, err := hex.DecodeString(s)
	return err == nil
}

func v7r7Name(s string) bool {
	if len(s) == 0 || len(s) > 128 { return false }
	for _, r := range s {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' || r == '-' { continue }
		return false
	}
	return true
}

func v7r7Safe(line string) bool {
	if line == v7r7WaitingLine { return true }
	if !strings.HasPrefix(line, v7r7ChallengePrefix) { return false }
	parts := strings.Fields(strings.TrimPrefix(line, v7r7ChallengePrefix))
	if len(parts) != 3 || !strings.HasPrefix(parts[0], "codespace=") || !strings.HasPrefix(parts[1], "challenge=") || !strings.HasPrefix(parts[2], "image_identity_sha256=") { return false }
	return v7r7Name(strings.TrimPrefix(parts[0], "codespace=")) && v7r7Hex(strings.TrimPrefix(parts[1], "challenge="), 32) && v7r7Hex(strings.TrimPrefix(parts[2], "image_identity_sha256="), 64)
}

func v7r7WriteSecure(secure *os.File, line string) error {
	if _, err := fmt.Fprintln(secure, line); err != nil { return err }
	return secure.Sync()
}

func v7r7Fatal(original, secure *os.File, code string) {
	if original != nil { fmt.Fprintln(original, "PHASE_C_V19_7_36_V7R7_STATUS_CHANNEL_DENIED:"+code) } else { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_STATUS_CHANNEL_DENIED:"+code) }
	if secure != nil { _ = v7r7WriteSecure(secure, v7r7FailedClosedLine); secure.Close() }
	os.Exit(92)
}

func v7r7MirrorUntilWaiting(r, w *os.File, originalFD int, secure *os.File, done chan<- struct{}) {
	defer r.Close()
	if done != nil { defer close(done) }
	original := os.NewFile(uintptr(originalFD), "multiverse-original-stdout")
	if original == nil { v7r7Fatal(nil, secure, "ORIGINAL_STDOUT") }
	defer original.Close()
	reader := bufio.NewReaderSize(r, 4096)
	challengeSeen := false
	for {
		line, err := reader.ReadString('\n')
		if len(line) > 8192 { v7r7Fatal(original, secure, "STDOUT_LINE_TOO_LONG") }
		if line != "" {
			if _, werr := io.WriteString(original, line); werr != nil { v7r7Fatal(original, secure, "ORIGINAL_STDOUT_WRITE") }
			trimmed := strings.TrimSuffix(strings.TrimSuffix(line, "\n"), "\r")
			if strings.HasPrefix(trimmed, v7r7ChallengePrefix) {
				if challengeSeen || !v7r7Safe(trimmed) { v7r7Fatal(original, secure, "CHALLENGE_LINE") }
				if werr := v7r7WriteSecure(secure, trimmed); werr != nil { v7r7Fatal(original, secure, "CHALLENGE_WRITE") }
				challengeSeen = true
			}
			if trimmed == v7r7WaitingLine {
				if !challengeSeen { v7r7Fatal(original, secure, "WAITING_BEFORE_CHALLENGE") }
				if werr := v7r7WriteSecure(secure, trimmed); werr != nil { v7r7Fatal(original, secure, "WAITING_WRITE") }
				if werr := syscall.Dup2(originalFD, int(os.Stdout.Fd())); werr != nil { v7r7Fatal(original, secure, "STDOUT_RESTORE") }
				w.Close(); secure.Close(); return
			}
		}
		if err != nil {
			if err == io.EOF {
				if werr := v7r7WriteSecure(secure, v7r7FailedClosedLine); werr != nil { _ = os.Remove(v7r7SecureStatusPath) }
				secure.Close()
				return
			}
			v7r7Fatal(original, secure, "STDOUT_READ")
		}
	}
}

func v7r7CurrentFSUID() (uint32, error) {
	b, err := os.ReadFile("/proc/thread-self/status")
	if err != nil { return 0, err }
	for _, line := range strings.Split(string(b), "\n") {
		if !strings.HasPrefix(line, "Uid:") { continue }
		fields := strings.Fields(strings.TrimSpace(strings.TrimPrefix(line, "Uid:")))
		if len(fields) != 4 { return 0, fmt.Errorf("fsuid-shape") }
		n, err := strconv.ParseUint(fields[3], 10, 32)
		if err != nil { return 0, err }
		return uint32(n), nil
	}
	return 0, fmt.Errorf("fsuid-missing")
}

func v7r7SetFSUIDExact(uid uint32) error {
	_, _, _ = syscall.RawSyscall(syscall.SYS_SETFSUID, uintptr(uid), 0, 0)
	got, err := v7r7CurrentFSUID()
	if err != nil { return err }
	if got != uid { return fmt.Errorf("fsuid-mismatch:%d", got) }
	return nil
}

func v7r7OpenDirAt(parentFD int, leaf string) (int, error) {
	fd, err := syscall.Openat(parentFD, leaf, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
	if err != nil { return -1, err }
	var st syscall.Stat_t
	if err := syscall.Fstat(fd, &st); err != nil || st.Mode&syscall.S_IFMT != syscall.S_IFDIR { _ = syscall.Close(fd); return -1, fmt.Errorf("dir-class:%s", leaf) }
	return fd, nil
}

func v7r7RandomTempLeaf() (string, error) {
	var b [16]byte
	if _, err := io.ReadFull(rand.Reader, b[:]); err != nil { return "", err }
	return ".multiverse-v7r7-ui-" + hex.EncodeToString(b[:]) + ".tmp", nil
}

func v7r7AtomicMirrorAt(dirFD int, targetLeaf, content string) error {
	tmpLeaf, err := v7r7RandomTempLeaf()
	if err != nil { return err }
	fd, err := syscall.Openat(dirFD, tmpLeaf, syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0600)
	if err != nil { return err }
	cleanup := true
	defer func() { _ = syscall.Close(fd); if cleanup { _ = syscall.Unlinkat(dirFD, tmpLeaf) } }()
	f := os.NewFile(uintptr(fd), "v7r7-ui-mirror-temp")
	if f == nil { return fmt.Errorf("ui-temp-file") }
	if _, err := io.WriteString(f, content); err != nil { return err }
	if err := f.Sync(); err != nil { return err }
	if err := syscall.Fchmod(fd, 0444); err != nil { return err }
	var st syscall.Stat_t
	if err := syscall.Fstat(fd, &st); err != nil || st.Mode&syscall.S_IFMT != syscall.S_IFREG { return fmt.Errorf("ui-temp-class") }
	if err := syscall.Renameat(dirFD, tmpLeaf, dirFD, targetLeaf); err != nil { return err }
	cleanup = false
	return syscall.Fsync(dirFD)
}

func v7r7ReplaceUIMirror(ruid uint32) error {
	if fsuid, err := v7r7CurrentFSUID(); err != nil || fsuid != 0 { return fmt.Errorf("fsuid-root-precondition") }
	rootFD, err := syscall.Open("/", syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC, 0)
	if err != nil { return fmt.Errorf("ui-root-open") }
	defer syscall.Close(rootFD)
	if err := v7r7SetFSUIDExact(ruid); err != nil { return fmt.Errorf("fsuid-owner-enter") }
	restore := true
	defer func() { if restore { _ = v7r7SetFSUIDExact(0) } }()
	workFD, err := v7r7OpenDirAt(rootFD, "workspaces")
	if err != nil { return fmt.Errorf("ui-workspaces-bind") }
	defer syscall.Close(workFD)
	repoFD, err := v7r7OpenDirAt(workFD, "multiverse-research")
	if err != nil { return fmt.Errorf("ui-repo-bind") }
	defer syscall.Close(repoFD)
	var repoStat syscall.Stat_t
	if err := syscall.Fstat(repoFD, &repoStat); err != nil || repoStat.Uid != ruid || repoStat.Mode&syscall.S_IFMT != syscall.S_IFDIR { return fmt.Errorf("ui-repo-class") }
	mirror := strings.Join([]string{v7r7ArmedLine, "ui_mirror=NONAUTHORITATIVE_STATIC", "authoritative_status_path=" + v7r7SecureStatusPath, "next_action=FOLLOW_TERMINAL_AND_CORE_ONLY", "runtime=OFF", ""}, "\n")
	if err := v7r7AtomicMirrorAt(repoFD, v7r7UIControlLeaf, mirror); err != nil { return fmt.Errorf("ui-atomic-replace") }
	if err := v7r7SetFSUIDExact(0); err != nil { return fmt.Errorf("fsuid-root-restore") }
	restore = false
	return nil
}

func v7r7OpenSecureStatus() (*os.File, error) {
	if fsuid, err := v7r7CurrentFSUID(); err != nil || fsuid != 0 { return nil, fmt.Errorf("secure-fsuid-root") }
	if err := os.Mkdir(v7r7SecureStatusDir, 0700); err != nil && !os.IsExist(err) { return nil, err }
	var dirStat syscall.Stat_t
	if err := syscall.Lstat(v7r7SecureStatusDir, &dirStat); err != nil || dirStat.Uid != 0 || dirStat.Mode&syscall.S_IFMT != syscall.S_IFDIR { return nil, fmt.Errorf("secure-dir-class") }
	if err := os.Chmod(v7r7SecureStatusDir, 0700); err != nil { return nil, fmt.Errorf("secure-dir-mode") }
	fd, err := syscall.Open(v7r7SecureStatusPath, syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0600)
	if err != nil { return nil, err }
	f := os.NewFile(uintptr(fd), "v7r7-authoritative-status")
	if f == nil { _ = syscall.Close(fd); return nil, fmt.Errorf("secure-file") }
	var st syscall.Stat_t
	if err := syscall.Fstat(fd, &st); err != nil || st.Uid != 0 || st.Mode&syscall.S_IFMT != syscall.S_IFREG { f.Close(); _ = os.Remove(v7r7SecureStatusPath); return nil, fmt.Errorf("secure-class") }
	if err := f.Chmod(0400); err != nil { f.Close(); _ = os.Remove(v7r7SecureStatusPath); return nil, fmt.Errorf("secure-mode") }
	return f, nil
}

func v7r7CleanupSecure(secure *os.File) {
	if secure != nil { secure.Close() }
	_ = os.Remove(v7r7SecureStatusPath)
	_ = os.Remove(v7r7SecureStatusDir)
}

func v7r7OpenChannels(ruid uint32) (*os.File, error) {
	secure, err := v7r7OpenSecureStatus()
	if err != nil { return nil, err }
	if err := v7r7ReplaceUIMirror(ruid); err != nil { v7r7CleanupSecure(secure); return nil, err }
	for _, line := range []string{v7r7ArmedLine, "timer_state=STARTING_TRUSTED_GITHUB_SERVER_TIME", "runtime=OFF"} {
		if err := v7r7WriteSecure(secure, line); err != nil { v7r7CleanupSecure(secure); return nil, err }
	}
	return secure, nil
}

func v7r7Install() error {
	x := os.Getenv("MULTIVERSE_V7R7_ARM_RUID")
	n, err := strconv.ParseUint(x, 10, 32)
	if err != nil || n == 0 { return fmt.Errorf("arm-ruid") }
	secure, err := v7r7OpenChannels(uint32(n))
	if err != nil { return err }
	originalFD, err := syscall.Dup(int(os.Stdout.Fd()))
	if err != nil { _ = v7r7WriteSecure(secure, v7r7FailedClosedLine); secure.Close(); return err }
	r, w, err := os.Pipe()
	if err != nil { syscall.Close(originalFD); _ = v7r7WriteSecure(secure, v7r7FailedClosedLine); secure.Close(); return err }
	if err := syscall.Dup2(int(w.Fd()), int(os.Stdout.Fd())); err != nil { r.Close(); w.Close(); syscall.Close(originalFD); _ = v7r7WriteSecure(secure, v7r7FailedClosedLine); secure.Close(); return err }
	go v7r7MirrorUntilWaiting(r, w, originalFD, secure, nil)
	return nil
}

func v7r7Selftest() {
	good := v7r7ChallengePrefix + "codespace=studious-halibut challenge=" + strings.Repeat("a", 32) + " image_identity_sha256=" + strings.Repeat("b", 64)
	if !v7r7Safe(good) || !v7r7Safe(v7r7WaitingLine) || v7r7Safe(good+" device_code=NO") || v7r7Safe("device code 1234-5678") { panic("v7r7-safe-lines") }
	td, err := os.MkdirTemp("", "multiverse-v7r7-status-")
	if err != nil { panic("temp") }
	defer os.RemoveAll(td)
	secure, _ := os.OpenFile(td+"/secure", os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	old, _ := syscall.Dup(int(os.Stdout.Fd()))
	captureR, captureW, _ := os.Pipe(); sourceR, sourceW, _ := os.Pipe()
	_ = syscall.Dup2(int(sourceW.Fd()), int(os.Stdout.Fd()))
	done := make(chan struct{})
	go v7r7MirrorUntilWaiting(sourceR, sourceW, int(captureW.Fd()), secure, done)
	fmt.Println(good); fmt.Println(v7r7WaitingLine)
	select { case <-done: case <-time.After(2 * time.Second): panic("mirror-timeout") }
	const downstream = "DEVICE_CODE_SHOULD_REMAIN_TERMINAL_ONLY_AFTER_RESTORE"
	fmt.Println(downstream)
	_ = syscall.Dup2(old, int(os.Stdout.Fd())); syscall.Close(old); captureW.Close()
	captured, _ := io.ReadAll(captureR); captureR.Close(); sb, _ := os.ReadFile(td + "/secure")
	if !strings.Contains(string(captured), downstream) || strings.Contains(string(sb), downstream) || !strings.Contains(string(sb), good) || !strings.Contains(string(sb), v7r7WaitingLine) { panic("persistence-boundary") }

	bound := td + "/bound"; moved := td + "/moved"
	if err := os.Mkdir(bound, 0755); err != nil { panic("bound-mkdir") }
	control := bound + "/" + v7r7UIControlLeaf
	if err := os.WriteFile(control, []byte("OLD\n"), 0644); err != nil { panic("control-old") }
	retained, err := os.OpenFile(control, os.O_WRONLY|os.O_APPEND, 0); if err != nil { panic("retained-open") }
	dirFD, err := syscall.Open(bound, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC, 0); if err != nil { panic("dirfd-open") }
	if err := os.Rename(bound, moved); err != nil { panic("bound-rename") }
	if err := os.Mkdir(bound, 0755); err != nil { panic("replacement-mkdir") }
	if err := os.WriteFile(bound+"/"+v7r7UIControlLeaf, []byte("DECOY\n"), 0644); err != nil { panic("decoy") }
	if err := v7r7AtomicMirrorAt(dirFD, v7r7UIControlLeaf, "BOUND_NONAUTHORITY\n"); err != nil { panic("atomic-mirror") }
	if _, err := retained.WriteString("RETAINED_FD_TAMPER\n"); err != nil { panic("retained-write") }
	retained.Close(); syscall.Close(dirFD)
	movedNow, _ := os.ReadFile(moved + "/" + v7r7UIControlLeaf); decoyNow, _ := os.ReadFile(bound + "/" + v7r7UIControlLeaf)
	if strings.Contains(string(movedNow), "RETAINED_FD_TAMPER") || string(movedNow) != "BOUND_NONAUTHORITY\n" || string(decoyNow) != "DECOY\n" { panic("descriptor-path-binding") }
	fmt.Println("PHASE_C_V19_7_36_V7R7_ATTACH_READY_OBSERVABILITY_SELFTEST_PASS")
	fmt.Println("PHASE_C_V19_7_36_V7R7_ATTACH_READY_OBSERVABILITY_BEHAVIOR_SELFTEST_PASS")
	fmt.Println("PHASE_C_V19_7_36_V7R7_UI_RETAINED_FD_ATOMIC_REPLACE_PASS")
	fmt.Println("PHASE_C_V19_7_36_V7R7_UI_DIRECTORY_FD_BINDING_PASS")
}

func init() {
	if len(os.Args) == 2 && os.Args[1] == "build-selftest" { v7r7Selftest(); return }
	if os.Getenv("CODESPACES") != "true" || os.Geteuid() != 0 { return }
	runtime.LockOSThread()
	if err := v7r7Install(); err != nil { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_STATUS_CHANNEL_DENIED:"+err.Error()); os.Exit(92) }
}
