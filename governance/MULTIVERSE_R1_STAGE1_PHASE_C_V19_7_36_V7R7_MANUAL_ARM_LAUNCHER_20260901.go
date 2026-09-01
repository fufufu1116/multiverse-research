package main

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"runtime"
	"strconv"
	"strings"
	"syscall"
)

const gatePath = "/usr/local/sbin/multiverse-v36-session-gate-v7r7"
const controlPath = "/workspaces/multiverse-research/MULTIVERSE_PRELIVE_START_HERE.md"
const readyPath = "/workspaces/.codespaces/.persistedshare/multiverse-v36-v7r7-ui-ready.txt"
const sessionPath = "/workspaces/.codespaces/.persistedshare/multiverse-v36-v7r7-session-status.txt"
const lockPath = "/run/multiverse-v36-v7r7-arm.lock"
const armPath = "/usr/local/bin/multiverse-v36-arm-v7r7"
const imageIdentityPathV7R7 = "/opt/multiverse/v36/image-identity-v7r3.json"
const prSetNoNewPrivs = 38

func deny(code string) {
	fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_ARM_LAUNCHER_DENIED:"+code)
	os.Exit(92)
}

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
		return "", errors.New("identity-class")
	}
	b, err := io.ReadAll(io.LimitReader(f, (1<<20)+1))
	if err != nil || len(b) == 0 || len(b) > 1<<20 {
		return "", errors.New("identity-read")
	}
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:]), nil
}

func expectedReady(name, identity string) string {
	return "PHASE_C_V19_7_36_V7R7_UI_READY\n" +
		"codespace=" + name + "\n" +
		"image_identity_sha256=" + identity + "\n" +
		"timer_state=NOT_STARTED\n" +
		"arm_state=NOT_STARTED\n" +
		"arm_command=" + armPath + "\n" +
		"next_action=RETURN_TO_CORE_BEFORE_ARM\n" +
		"runtime=OFF\n"
}

func expectedControl(name, identity string) string {
	return "# MULTIVERSE PRE-LIVE CONTROL — V19.7.36 v7r7\n\n" +
		"`PHASE_C_V19_7_36_V7R7_UI_READY`\n\n" +
		"- codespace=`" + name + "`\n" +
		"- image_identity_sha256=`" + identity + "`\n" +
		"- timer_state=`NOT_STARTED`\n" +
		"- arm_state=`NOT_STARTED`\n" +
		"- next_action=`RETURN_TO_CORE_BEFORE_ARM`\n" +
		"- runtime=`OFF`\n\n" +
		"The strict 600-second challenge window has not started. Do not run the arm command until Core Fresh-rebinds this Codespace and exact image identity and explicitly says to arm.\n\n" +
		"Reviewed arm command (do not run yet): `" + armPath + "`\n"
}

func openedExact(path, want string, uid uint32, mode uint32) error {
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
	if st.Uid != uid || st.Mode&syscall.S_IFMT != syscall.S_IFREG || uint32(st.Mode)&0777 != mode {
		return errors.New("class")
	}
	b, err := io.ReadAll(io.LimitReader(f, 1<<20))
	if err != nil || string(b) != want {
		return errors.New("content")
	}
	return nil
}

func rootDir(path string) error {
	var st syscall.Stat_t
	if err := syscall.Lstat(path, &st); err != nil {
		return err
	}
	if st.Uid != 0 || st.Mode&syscall.S_IFMT != syscall.S_IFDIR || st.Mode&0022 != 0 {
		return errors.New("dir-class")
	}
	return nil
}

func enableNoNewPrivs() error {
	_, _, e := syscall.RawSyscall6(syscall.SYS_PRCTL, uintptr(prSetNoNewPrivs), 1, 0, 0, 0, 0)
	if e != 0 {
		return e
	}
	b, err := os.ReadFile("/proc/self/status")
	if err != nil || !strings.Contains(string(b), "NoNewPrivs:\t1") {
		return errors.New("nnp-not-set")
	}
	return nil
}

func capsNarrow() error {
	b, err := os.ReadFile("/proc/self/status")
	if err != nil {
		return err
	}
	get := func(k string) uint64 {
		for _, l := range strings.Split(string(b), "\n") {
			if strings.HasPrefix(l, k+":") {
				v, _ := strconv.ParseUint(strings.TrimSpace(strings.TrimPrefix(l, k+":")), 16, 64)
				return v
			}
		return ^uint64(0)
	}
	allowed := uint64((1 << 0) | (1 << 6) | (1 << 7))
	if get("CapEff")&^allowed != 0 || get("CapBnd")&^allowed != 0 {
		return errors.New("caps")
	}
	return nil
}

func openGateFD3() error {
	fd, err := syscall.Open(gatePath, syscall.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return err
	}
	var st syscall.Stat_t
	if err := syscall.Fstat(fd, &st); err != nil {
		syscall.Close(fd)
		return err
	}
	if st.Uid != 0 || st.Mode&syscall.S_IFMT != syscall.S_IFREG || uint32(st.Mode)&0777 != 0555 {
		syscall.Close(fd)
		return errors.New("gate-class")
	}
	if fd != 3 {
		if err := syscall.Dup3(fd, 3, 0); err != nil {
			syscall.Close(fd)
			return err
		}
		syscall.Close(fd)
	}
	return nil
}

func main() {
	if runtime.GOOS != "linux" || runtime.GOARCH != "amd64" || len(os.Args) != 1 {
		deny("PLATFORM_OR_ARGS")
	}
	ruid := os.Getuid()
	if ruid == 0 || os.Geteuid() != 0 {
		deny("SETUID_BOUNDARY")
	}
	if err := syscall.Setresuid(0, 0, 0); err != nil || os.Getuid() != 0 || os.Geteuid() != 0 {
		deny("ROOT_NORMALIZE")
	}
	if err := enableNoNewPrivs(); err != nil {
		deny("NO_NEW_PRIVS")
	}
	if err := capsNarrow(); err != nil {
		deny("CAPS")
	}
	codespaces := os.Getenv("CODESPACES")
	name := os.Getenv("CODESPACE_NAME")
	os.Clearenv()
	if codespaces != "true" {
		deny("CODESPACES")
	}
	if !validName(name) {
		deny("CODESPACE_NAME")
	}
	identity, err := imageIdentitySHA256()
	if err != nil {
		deny("IMAGE_IDENTITY")
	}
	if err := openedExact(readyPath, expectedReady(name, identity), uint32(ruid), 0444); err != nil {
		deny("READY_BINDING")
	}
	if err := openedExact(controlPath, expectedControl(name, identity), uint32(ruid), 0644); err != nil {
		deny("CONTROL_BINDING")
	}
	if _, err := os.Lstat(sessionPath); err == nil {
		deny("SESSION_STATUS_PREEXISTS")
	} else if !os.IsNotExist(err) {
		deny("SESSION_STATUS_STAT")
	}
	if err := rootDir("/run"); err != nil {
		deny("RUN_CLASS")
	}
	lockFD, err := syscall.Open(lockPath, syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0400)
	if err != nil {
		deny("ARM_LOCK")
	}
	lock := os.NewFile(uintptr(lockFD), "arm-lock")
	if _, err := fmt.Fprintf(lock, "codespace=%s\nimage_identity_sha256=%s\noriginal_uid=%d\nruntime=OFF\n", name, identity, ruid); err != nil || lock.Sync() != nil || lock.Close() != nil {
		deny("ARM_LOCK_WRITE")
	}
	if err := openGateFD3(); err != nil {
		deny("GATE_CLASS")
	}
	for fd := 4; fd < 1024; fd++ {
		_ = syscall.Close(fd)
	}
	env := []string{"CODESPACES=true", "CODESPACE_NAME=" + name, "MULTIVERSE_V7R7_ARM_RUID=" + strconv.Itoa(ruid), "LANG=C", "LC_ALL=C"}
	fmt.Printf("PHASE_C_V19_7_36_V7R7_ARM_START codespace=%s image_identity_sha256=%s timer_starts_inside_session_gate_after_trusted_server_time runtime=OFF\n", name, identity)
	if err := syscall.Exec("/proc/self/fd/3", []string{gatePath}, env); err != nil {
		deny("EXEC_GATE")
	}
}
