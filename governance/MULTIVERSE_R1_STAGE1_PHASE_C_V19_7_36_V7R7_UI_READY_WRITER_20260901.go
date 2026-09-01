package main

import (
	"crypto/sha256"
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
const imageIdentityPathV7R7 = "/opt/multiverse/v36/image-identity-v7r3.json"

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

func imageIdentitySHA256() (string, error) {
	fd, err := syscall.Open(imageIdentityPathV7R7, syscall.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
	if err != nil {
		return "", err
	}
	f := os.NewFile(uintptr(fd), imageIdentityPathV7R7)
	defer f.Close()
	var st syscall.Stat_t
	if err := syscall.Fstat(fd, &st); err != nil {
		return "", err
	}
	if st.Uid != 0 || st.Mode&syscall.S_IFMT != syscall.S_IFREG || uint32(st.Mode)&0777 != 0444 || st.Size <= 0 || st.Size > 1<<20 {
		return "", fmt.Errorf("image-identity-class")
	}
	b, err := io.ReadAll(io.LimitReader(f, (1<<20)+1))
	if err != nil || len(b) == 0 || len(b) > 1<<20 {
		return "", fmt.Errorf("image-identity-read")
	}
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:]), nil
}

func exactReady(name, identity string) string {
	return "PHASE_C_V19_7_36_V7R7_UI_READY\n" +
		"codespace=" + name + "\n" +
		"image_identity_sha256=" + identity + "\n" +
		"timer_state=NOT_STARTED\n" +
		"arm_state=NOT_STARTED\n" +
		"arm_command=" + armCommand + "\n" +
		"next_action=RETURN_TO_CORE_BEFORE_ARM\n" +
		"runtime=OFF\n"
}

func controlReady(name, identity string) string {
	return "# MULTIVERSE PRE-LIVE CONTROL — V19.7.36 v7r7\n\n" +
		"`PHASE_C_V19_7_36_V7R7_UI_READY`\n\n" +
		"- codespace=`" + name + "`\n" +
		"- image_identity_sha256=`" + identity + "`\n" +
		"- timer_state=`NOT_STARTED`\n" +
		"- arm_state=`NOT_STARTED`\n" +
		"- next_action=`RETURN_TO_CORE_BEFORE_ARM`\n" +
		"- runtime=`OFF`\n\n" +
		"The strict 600-second challenge window has not started. Do not run the arm command until Core Fresh-rebinds this Codespace and exact image identity and explicitly says to arm.\n\n" +
		"Reviewed arm command (do not run yet): `" + armCommand + "`\n"
}

func existingReadyExact(path, want string, uid uint32) error {
	fd, err := syscall.Open(path, syscall.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
	if err != nil {
		return err
	}
	f := os.NewFile(uintptr(fd), path)
	defer f.Close()
	var st syscall.Stat_t
	if err := syscall.Fstat(fd, &st); err != nil {
		return err
	}
	if st.Uid != uid || st.Mode&syscall.S_IFMT != syscall.S_IFREG || uint32(st.Mode)&0777 != 0444 {
		return fmt.Errorf("ready-class")
	}
	b, err := io.ReadAll(io.LimitReader(f, 1<<20))
	if err != nil || string(b) != want {
		return fmt.Errorf("ready-content")
	}
	return nil
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
	if st.Uid != uid || st.Mode&syscall.S_IFMT != syscall.S_IFREG || uint32(st.Mode)&0777 != 0644 {
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
	identity, err := imageIdentitySHA256()
	if err != nil {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:IMAGE_IDENTITY")
		os.Exit(92)
	}
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
	ready := exactReady(name, identity)
	fd, err := syscall.Open(uiReadyPath, syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0444)
	if err != nil {
		if !os.IsExist(err) || existingReadyExact(uiReadyPath, ready, uint32(os.Geteuid())) != nil {
			fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:READY_STALE_OR_AMBIGUOUS")
			os.Exit(92)
		}
	} else {
		f := os.NewFile(uintptr(fd), uiReadyPath)
		if _, err := io.WriteString(f, ready); err != nil || f.Sync() != nil || f.Chmod(0444) != nil || f.Close() != nil {
			fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:READY_WRITE")
			os.Exit(92)
		}
		if err := existingReadyExact(uiReadyPath, ready, uint32(os.Geteuid())); err != nil {
			fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:READY_VERIFY")
			os.Exit(92)
		}
	}
	if err := writeNoFollow(uiControlPath, controlReady(name, identity), uint32(os.Geteuid())); err != nil {
		fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:CONTROL_WRITE:"+strings.ReplaceAll(err.Error(), "\n", "_"))
		os.Exit(92)
	}
	fmt.Printf("PHASE_C_V19_7_36_V7R7_UI_READY_WRITER_PASS image_identity_sha256=%s timer_state=NOT_STARTED runtime=OFF\n", identity)
}
