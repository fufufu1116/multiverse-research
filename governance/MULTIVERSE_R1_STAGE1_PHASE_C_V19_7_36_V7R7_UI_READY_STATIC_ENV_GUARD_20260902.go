package main

import (
	"crypto/sha256"
	"fmt"
	"io"
	"os"
	"runtime"
	"syscall"
)

const helperPath = "/usr/local/bin/multiverse-v36-ui-ready-v7r7"
const expectedHelperSHA256 = "2fd9e085e866924fb52995e5bb5fcb58763bdbd1fa1ee2c96e1d57df28a42301"

func deny(code string) {
	fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_ENV_GUARD_DENIED:"+code)
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

func verifyHelper() {
	fd, err := syscall.Open(helperPath, syscall.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
	if err != nil {
		deny("HELPER_OPEN")
	}
	f := os.NewFile(uintptr(fd), helperPath)
	defer f.Close()
	var st syscall.Stat_t
	if err := syscall.Fstat(fd, &st); err != nil {
		deny("HELPER_STAT")
	}
	if st.Uid != 0 || st.Gid != 0 || st.Mode&syscall.S_IFMT != syscall.S_IFREG || uint32(st.Mode)&0777 != 0555 || st.Size <= 0 || st.Size > 64<<20 {
		deny("HELPER_CLASS")
	}
	h := sha256.New()
	if _, err := io.Copy(h, io.LimitReader(f, (64<<20)+1)); err != nil {
		deny("HELPER_HASH")
	}
	if fmt.Sprintf("%x", h.Sum(nil)) != expectedHelperSHA256 {
		deny("HELPER_IDENTITY")
	}
}

func main() {
	if runtime.GOOS != "linux" || runtime.GOARCH != "amd64" || len(os.Args) != 2 {
		deny("PLATFORM_OR_ARGS")
	}
	uid := os.Getuid()
	if uid == 0 || os.Geteuid() != uid {
		deny("USER_BOUNDARY")
	}
	if os.Getenv("CODESPACES") != "true" {
		deny("CODESPACES")
	}
	name := os.Getenv("CODESPACE_NAME")
	if !validName(name) || name != os.Args[1] {
		deny("CODESPACE_NAME")
	}

	// Only CODESPACES and CODESPACE_NAME are captured. The process environment
	// is then erased before helper verification and the exact execve below.
	os.Clearenv()
	verifyHelper()

	env := []string{"CODESPACES=true", "CODESPACE_NAME=" + name}
	argv := []string{helperPath}
	fmt.Printf("PHASE_C_V19_7_36_V7R7_UI_READY_ENV_GUARD_PASS codespace=%s child_env=EXACT_COSPACES_AND_NAME_ONLY helper_sha256=%s runtime=OFF\n", name, expectedHelperSHA256)
	if err := syscall.Exec(helperPath, argv, env); err != nil {
		deny("EXEC")
	}
}
