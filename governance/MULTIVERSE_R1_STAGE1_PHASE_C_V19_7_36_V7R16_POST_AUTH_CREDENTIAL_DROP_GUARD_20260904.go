package main

import (
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "io"
    "os"
    "runtime"
    "strconv"
    "strings"
    "syscall"
    "unsafe"
)

const (
    helperPath = "/usr/local/bin/multiverse-v36-ui-ready-v7r7"
    expectedHelperSHA256 = "2fd9e085e866924fb52995e5bb5fcb58763bdbd1fa1ee2c96e1d57df28a42301"
    authorityUID = 64173
    prSetDumpable = 4
    prGetDumpable = 3
    fGetFD = 1
    fSetFD = 2
    fdCloexec = 1
    fGetSeals = 1034
    fSealSeal = 0x0001
    fSealShrink = 0x0002
    fSealGrow = 0x0004
    fSealWrite = 0x0008
    requiredSeals = fSealSeal | fSealShrink | fSealGrow | fSealWrite
)

type authoritySnapshot struct {
    Version string `json:"version"`
    Generation string `json:"generation"`
    Codespace string `json:"codespace"`
    Mode string `json:"mode"`
    Reason string `json:"reason"`
    Before int `json:"before"`
    After int `json:"after"`
    Reset int64 `json:"reset"`
    StatusSHA256 string `json:"status_sha256"`
    ControlSHA256 string `json:"control_sha256"`
    Runtime string `json:"runtime"`
}

func deny(code string) {
    fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R16_POST_AUTH_DROP_GUARD_DENIED:"+code)
    os.Exit(92)
}

func validName(s string) bool {
    if len(s) == 0 || len(s) > 128 { return false }
    for _, r := range s {
        if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '-' { continue }
        return false
    }
    return true
}

func validGeneration(s string) bool {
    if len(s) != 32 { return false }
    _, err := hex.DecodeString(s)
    return err == nil && strings.ToLower(s) == s
}

func validSHA256(s string) bool {
    if len(s) != 64 { return false }
    _, err := hex.DecodeString(s)
    return err == nil && strings.ToLower(s) == s
}

func getResUIDs() (uint32,uint32,uint32,error) {
    var r,e,s uint32
    _,_,er := syscall.Syscall(syscall.SYS_GETRESUID, uintptr(unsafe.Pointer(&r)), uintptr(unsafe.Pointer(&e)), uintptr(unsafe.Pointer(&s)))
    if er != 0 { return 0,0,0,er }
    return r,e,s,nil
}

func setFSUIDAndVerify(uid uint32) error {
    if _,_,er := syscall.Syscall(syscall.SYS_SETFSUID, uintptr(uid), 0, 0); er != 0 { return er }
    cur,_,er := syscall.Syscall(syscall.SYS_SETFSUID, ^uintptr(0), 0, 0)
    if er != 0 { return er }
    if uint32(cur) != uid { return fmt.Errorf("fsuid-mismatch") }
    return nil
}

func setNondumpable() error {
    if _,_,er := syscall.Syscall6(syscall.SYS_PRCTL, uintptr(prSetDumpable), 0,0,0,0,0); er != 0 { return er }
    v,_,er := syscall.Syscall6(syscall.SYS_PRCTL, uintptr(prGetDumpable), 0,0,0,0,0)
    if er != 0 { return er }
    if v != 0 { return fmt.Errorf("dumpable-not-zero") }
    return nil
}

func verifyNoTracer() error {
    b,err := os.ReadFile("/proc/self/status")
    if err != nil { return err }
    for _,ln := range strings.Split(string(b), "\n") {
        if strings.HasPrefix(ln,"TracerPid:") {
            if strings.TrimSpace(strings.TrimPrefix(ln,"TracerPid:")) != "0" { return fmt.Errorf("tracer-present") }
            return nil
        }
    }
    return fmt.Errorf("tracerpid-missing")
}

func verifyProtectedCredentialBoundary() (uint32,error) {
    r,e,s,err := getResUIDs()
    if err != nil { return 0,err }
    if r == 0 || r == authorityUID || e != authorityUID || s != authorityUID { return 0,fmt.Errorf("credential-mismatch") }
    if err = setNondumpable(); err != nil { return 0,err }
    if err = verifyNoTracer(); err != nil { return 0,err }
    return r,nil
}

func verifySecureRuntimeEnv(name string) error {
    envs := os.Environ()
    if len(envs) != 3 { return fmt.Errorf("env-count") }
    want := map[string]int{"CODESPACES=true":0,"CODESPACE_NAME="+name:0,"GOTRACEBACK=none":0}
    for _,v := range envs {
        if _,ok := want[v]; !ok { return fmt.Errorf("env-unexpected") }
        want[v]++
    }
    for _,n := range want { if n != 1 { return fmt.Errorf("env-duplicate-or-missing") } }
    return nil
}

func verifyAuthorityFD(fd int, name, generation string) (authoritySnapshot,string,error) {
    var zero authoritySnapshot
    if fd < 3 || fd > 4096 { return zero,"",fmt.Errorf("fd-range") }
    flags,_,er := syscall.Syscall(syscall.SYS_FCNTL, uintptr(fd), uintptr(fGetFD), 0)
    if er != 0 { return zero,"",er }
    if int(flags)&fdCloexec != 0 { return zero,"",fmt.Errorf("fd-still-cloexec") }
    if _,_,er = syscall.Syscall(syscall.SYS_FCNTL, uintptr(fd), uintptr(fSetFD), uintptr(fdCloexec)); er != 0 { return zero,"",er }
    seals,_,er := syscall.Syscall(syscall.SYS_FCNTL, uintptr(fd), uintptr(fGetSeals), 0)
    if er != 0 { return zero,"",er }
    if int(seals)&requiredSeals != requiredSeals { return zero,"",fmt.Errorf("seal-set-incomplete") }
    var st syscall.Stat_t
    if err := syscall.Fstat(fd,&st); err != nil { return zero,"",err }
    if st.Mode&syscall.S_IFMT != syscall.S_IFREG || st.Nlink != 0 || st.Size <= 0 || st.Size > 64<<10 { return zero,"",fmt.Errorf("authority-class") }
    f := os.NewFile(uintptr(fd),"v7r16-authority")
    if f == nil { return zero,"",fmt.Errorf("authority-file") }
    if _,err := f.Seek(0,0); err != nil { return zero,"",err }
    b,err := io.ReadAll(io.LimitReader(f, (64<<10)+1))
    if err != nil || len(b) == 0 || len(b) > 64<<10 { return zero,"",fmt.Errorf("authority-read") }
    if b[len(b)-1] != '\n' { return zero,"",fmt.Errorf("authority-newline") }
    dec := json.NewDecoder(strings.NewReader(string(b)))
    dec.DisallowUnknownFields()
    var snap authoritySnapshot
    if err := dec.Decode(&snap); err != nil { return zero,"",fmt.Errorf("authority-json") }
    var extra any
    if err := dec.Decode(&extra); err != io.EOF { return zero,"",fmt.Errorf("authority-extra") }
    if snap.Version != "V19.7.36-v7r15" || snap.Generation != generation || snap.Codespace != name || snap.Mode != "commit" || snap.Reason != "READY" || snap.Runtime != "OFF" { return zero,"",fmt.Errorf("authority-binding") }
    if !validGeneration(snap.Generation) || !validSHA256(snap.StatusSHA256) || !validSHA256(snap.ControlSHA256) { return zero,"",fmt.Errorf("authority-format") }
    if snap.Before < 60 || snap.After < 59 || snap.After != snap.Before-1 || snap.Reset <= 0 { return zero,"",fmt.Errorf("authority-rate") }
    h := sha256.Sum256(b)
    return snap,hex.EncodeToString(h[:]),nil
}

func verifyHelper() {
    fd,err := syscall.Open(helperPath, syscall.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC,0)
    if err != nil { deny("HELPER_OPEN") }
    f := os.NewFile(uintptr(fd),helperPath)
    defer f.Close()
    var st syscall.Stat_t
    if err := syscall.Fstat(fd,&st); err != nil { deny("HELPER_STAT") }
    if st.Uid != 0 || st.Gid != 0 || st.Mode&syscall.S_IFMT != syscall.S_IFREG || uint32(st.Mode)&0777 != 0555 || st.Size <= 0 || st.Size > 64<<20 { deny("HELPER_CLASS") }
    h := sha256.New()
    if _,err := io.Copy(h,io.LimitReader(f,(64<<20)+1)); err != nil { deny("HELPER_HASH") }
    if fmt.Sprintf("%x",h.Sum(nil)) != expectedHelperSHA256 { deny("HELPER_IDENTITY") }
}

// retireAuthorityBeforeUserDrop is the v7r16 security boundary. Every
// authorization-bearing read/decision has already completed while
// euid/suid=authorityUID. This function only retires the already-verified
// sealed authority descriptor while the process is still protected. After it
// returns there is no authority FD and no later authority re-read or
// authorization decision is permitted.
func retireAuthorityBeforeUserDrop(fd int) error {
    if err := syscall.Close(fd); err != nil { return err }
    var st syscall.Stat_t
    if err := syscall.Fstat(fd,&st); err == nil || err != syscall.EBADF { return fmt.Errorf("authority-fd-not-retired") }
    return nil
}

// dropToOrdinaryUser is intentionally the final authority-transition syscall.
// fsuid is moved to the target while the process is still protected, then all
// real/effective/saved UIDs are irreversibly set to the ordinary user. There
// are no security-critical checks, authority FD accesses, privilege-bearing
// operations, or authorization decisions after SYS_SETRESUID returns.
func dropToOrdinaryUser(uid uint32) error {
    if uid == 0 || uid == authorityUID { return fmt.Errorf("drop-target") }
    if err := setFSUIDAndVerify(uid); err != nil { return err }
    if _,_,er := syscall.Syscall(syscall.SYS_SETRESUID, uintptr(uid), uintptr(uid), uintptr(uid)); er != 0 { return er }
    return nil
}

func selftest() {
    if authorityUID != 64173 { panic("authority") }
    if !validName("abc-123") || validName("bad/name") { panic("name") }
    if !validGeneration("00112233445566778899aabbccddeeff") { panic("generation") }
    if !validSHA256(strings.Repeat("a",64)) { panic("sha") }
    fmt.Println("PHASE_C_V19_7_36_V7R16_POST_AUTH_DROP_GUARD_SELFTEST_PASS")
    fmt.Println("PROTECTED_GUARD_STARTUP_CREDENTIAL_MISMATCH_REQUIRED=true")
    fmt.Println("AUTHORITY_FD_RETIRED_BEFORE_ORDINARY_UID=true")
    fmt.Println("NO_POST_DROP_AUTHORIZATION_DECISION=true")
    fmt.Println("FINAL_AUTHORITY_TRANSITION_SYSCALL=SETRESUID")
    fmt.Println("SECURITY_AUTHORITY_GRANTED=false")
    fmt.Println("RUNTIME=OFF")
}

func main() {
    runtime.LockOSThread()
    if len(os.Args) == 2 && os.Args[1] == "build-selftest" { selftest(); return }
    if runtime.GOOS != "linux" || runtime.GOARCH != "amd64" || len(os.Args) != 4 { deny("PLATFORM_OR_ARGS") }
    name := os.Args[1]
    if !validName(name) { deny("CODESPACE_NAME") }
    fd,err := strconv.Atoi(os.Args[2])
    if err != nil { deny("AUTHORITY_FD") }
    generation := os.Args[3]
    if !validGeneration(generation) { deny("GENERATION") }
    uid,err := verifyProtectedCredentialBoundary()
    if err != nil { deny("PROTECTED_CREDENTIAL_BOUNDARY") }
    if err = verifySecureRuntimeEnv(name); err != nil { deny("SECURE_RUNTIME_ENV") }
    snap,authoritySHA,err := verifyAuthorityFD(fd,name,generation)
    if err != nil { deny("SEALED_AUTHORITY") }
    os.Clearenv()
    verifyHelper()
    if err = retireAuthorityBeforeUserDrop(fd); err != nil { deny("AUTHORITY_RETIREMENT") }

    // Everything printed before the user-drop is nonsecret machine evidence.
    // This marker establishes the structural boundary used by the independent
    // attack harness: after it appears the authority FD is already EBADF and
    // no subsequent code consults authority-bearing state.
    fmt.Printf("PHASE_C_V19_7_36_V7R16_AUTHORITY_RETIRED_BEFORE_USER_DROP codespace=%s generation=%s authority_sha256=%s rate=%d/%d runtime=OFF\n", name,generation,authoritySHA,snap.Before,snap.After)

    env := []string{"CODESPACES=true","CODESPACE_NAME="+name}
    argv := []string{helperPath}
    if err = dropToOrdinaryUser(uid); err != nil { deny("IRREVERSIBLE_USER_DROP") }

    // SECURITY BOUNDARY: after SYS_SETRESUID succeeds, only an ordinary-user
    // fixed-helper exec remains. No authority FD exists and there are no
    // authorization decisions to influence. Same-UID process-memory access
    // after this point is therefore outside the authority-bearing boundary.
    if err := syscall.Exec(helperPath,argv,env); err != nil {
        fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R16_POST_DROP_HELPER_EXEC_FAILED")
        os.Exit(92)
    }
}
