from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
import json
import os
import random
from datetime import datetime, date, timedelta


app = Flask(__name__)
app.secret_key = "ganti-dengan-kalimat-rahasia-kelompok-kalian"  # dibutuhkan untuk session

# ---------- Data akun (disimpan ke file users.json supaya tidak hilang) ----------
FILE_USER = os.path.join(os.path.dirname(__file__), "users.json")


def muat_users():
    try:
        with open(FILE_USER, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def simpan_users():
    with open(FILE_USER, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


users = muat_users()



@app.before_request
def cek_login():
    if request.endpoint in ("masuk", "daftar", "static"):
        return
    if session.get("user") not in users:
        session.clear()
        return redirect(url_for("masuk"))

rooms = [
    {"nama": "Ruang Diskusi A", "kapasitas": 6, "tersedia": True},
    {"nama": "Ruang Diskusi B", "kapasitas": 8, "tersedia": True},
    {"nama": "Lab Komputer 2", "kapasitas": 30, "tersedia": True},
]
events = [
    {"nama": "Seminar Teknologi AI", "tanggal": "20 Nov 2026", "kuota": 20},
    {"nama": "Lomba Coding Mahasiswa", "tanggal": "28 Nov 2026", "kuota": 10},
    {"nama": "Workshop Python Dasar", "tanggal": "5 Des 2026", "kuota": 15},
]

MAKS_JAM_PER_HARI = 4  # batas jam per orang per hari (ubah jadi 3 kalau mau lebih ketat)
bookings = []
# Loker A1-A10 sampai F1-F10. None = tersedia, kalau sudah dipinjam isinya nama peminjam
lokers = {}
for huruf in "ABCDEF":
    for angka in range(1, 11):
        lokers[huruf + str(angka)] = None
riwayat_loker = []
regs = []

rides = []

groups = [
    {"nama": "Belajar Python Dasar", "topik": "Pemrograman", "anggota": ["Zac"]},
    {"nama": "Kalkulus 1", "topik": "Matematika", "anggota": ["Henry", "Kevin"]},
]


def buat_kode(awalan):
    return awalan + "-" + str(random.randint(1000, 9999))


@app.route("/", methods=["GET", "POST"])
def reservasi():
    pesan = ""
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        ruang = request.form.get("ruang", "")
        tujuan = request.form.get("tujuan", "").strip()
        tanggal = request.form.get("tanggal", "")
        mulai = request.form.get("mulai", "")

        try:
            durasi = int(request.form.get("durasi", ""))
            awal = datetime.strptime(tanggal + " " + mulai, "%Y-%m-%d %H:%M")
        except ValueError:
            durasi = 0
            awal = None

        if nama == "" or tujuan == "":
            pesan = "Semua kolom wajib diisi ya!"
        elif awal is None or durasi < 1:
            pesan = "Tanggal, jam mulai, dan durasi harus diisi dengan benar."
        elif awal.date() < date.today():
            pesan = "Tanggal reservasi tidak boleh sudah lewat."
        elif durasi > MAKS_JAM_PER_HARI:
            pesan = f"Durasi maksimal {MAKS_JAM_PER_HARI} jam per hari."
        else:
            selesai = awal + timedelta(hours=durasi)
            terpakai = sum(b["durasi"] for b in bookings
                           if b["nama"].lower() == nama.lower() and b["tanggal"] == tanggal)

            if selesai.date() != awal.date():
                pesan = "Reservasi tidak boleh melewati tengah malam."
            elif terpakai + durasi > MAKS_JAM_PER_HARI:
                sisa = MAKS_JAM_PER_HARI - terpakai
                pesan = (f"Batas {MAKS_JAM_PER_HARI} jam per hari. Kamu sudah memesan "
                         f"{terpakai} jam pada tanggal itu (sisa {sisa} jam).")
            else:
                berhasil = False
                for r in rooms:
                    if r["nama"] == ruang and r["tersedia"]:
                        r["tersedia"] = False
                        kode = buat_kode("RSV")
                        waktu = (awal.strftime("%d-%m-%Y") + ", " + awal.strftime("%H:%M")
                                 + "-" + selesai.strftime("%H:%M") + f" ({durasi} jam)")
                        bookings.append({"kode": kode, "nama": nama, "ruang": ruang,
                                         "waktu": waktu, "tujuan": tujuan,
                                         "tanggal": tanggal, "durasi": durasi})
                        pesan = "Berhasil! Kode reservasi: " + kode
                        berhasil = True
                        break
                if not berhasil:
                    pesan = "Maaf, ruang itu sudah tidak tersedia."

    return render_template("reservasi.html", rooms=rooms, bookings=bookings,
                           pesan=pesan, aktif="reservasi", maks_jam=MAKS_JAM_PER_HARI)

@app.route("/kegiatan", methods=["GET", "POST"])
def kegiatan():
    pesan = ""
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        try:
            i = int(request.form.get("indeks", ""))
            e = events[i]
            if nama == "":
                pesan = "Isi nama dulu ya!"
            elif e["kuota"] < 1:
                pesan = "Maaf, kuota sudah penuh."
            else:
                e["kuota"] -= 1
                kode = buat_kode("EVT")
                regs.append({"kode": kode, "nama": nama, "kegiatan": e["nama"]})
                pesan = "Terdaftar! Kode: " + kode
        except (ValueError, IndexError):
            pesan = "Kegiatan tidak valid."

    return render_template("kegiatan.html", events=events, pesan=pesan, aktif="kegiatan")



@app.route("/kelompok", methods=["GET", "POST"])
def kelompok():
    pesan = ""
    if request.method == "POST":
        aksi = request.form.get("aksi", "")

        if aksi == "gabung":
            nama = request.form.get("nama", "").strip()
            try:
                g = groups[int(request.form.get("indeks", ""))]
                if nama == "":
                    pesan = "Isi nama dulu ya!"
                elif nama in g["anggota"]:
                    pesan = "Kamu sudah ada di kelompok ini."
                else:
                    g["anggota"].append(nama)
                    pesan = "Kamu bergabung ke " + g["nama"]
            except (ValueError, IndexError):
                pesan = "Kelompok tidak valid."

        elif aksi == "buat":
            nama = request.form.get("nama", "").strip()
            topik = request.form.get("topik", "").strip()
            pembuat = request.form.get("pembuat", "").strip()
            if nama == "" or topik == "" or pembuat == "":
                pesan = "Semua kolom wajib diisi ya!"
            else:
                groups.append({"nama": nama, "topik": topik, "anggota": [pembuat]})
                pesan = "Kelompok berhasil dibuat!"

    return render_template("kelompok.html", groups=groups, pesan=pesan, aktif="kelompok")




@app.route("/tumpangan", methods=["GET", "POST"])
def tumpangan():
    pesan = ""
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        jenis = request.form.get("jenis", "")
        rute = request.form.get("rute", "").strip()
        waktu = request.form.get("waktu", "").strip()
        if nama == "" or rute == "" or waktu == "":
            pesan = "Semua kolom wajib diisi ya!"
        else:
            rides.append({"nama": nama, "jenis": jenis, "rute": rute, "waktu": waktu})
            pesan = "Tumpangan tercatat!"

    return render_template("tumpangan.html", rides=rides, pesan=pesan, aktif="tumpangan")


@app.route("/ringkasan")
def ringkasan():
    return render_template("ringkasan.html", bookings=bookings, regs=regs,
                           groups=groups, rides=rides, aktif="ringkasan")


@app.route("/daftar", methods=["GET", "POST"])
def daftar():
    pesan = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        lahir = request.form.get("lahir", "")

        try:
            tgl = datetime.strptime(lahir, "%Y-%m-%d").date()
        except ValueError:
            tgl = None

        if len(username) < 3:
            pesan = "Username minimal 3 karakter."
        elif username.lower() in [u.lower() for u in users]:
            pesan = "Username sudah dipakai."
        elif len(password) < 6:
            pesan = "Password minimal 6 karakter."
        elif tgl is None or tgl > date.today():
            pesan = "Tanggal lahir tidak valid."
        else:
            users[username] = {
                "password": generate_password_hash(password),
                "lahir": lahir,
                "gabung": date.today().isoformat(),
            }
            simpan_users()
            return render_template("berhasil.html", judul="Pendaftaran berhasil!",
                                   keterangan="Akun kamu sudah dibuat. Silakan masuk.",
                                   tujuan=url_for("masuk"), tombol="Lanjut ke Login")

    return render_template("daftar.html", pesan=pesan, aktif="daftar")


@app.route("/masuk", methods=["GET", "POST"])
def masuk():
    pesan = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        data = users.get(username)

        if data is None or not check_password_hash(data["password"], password):
            pesan = "Username atau password salah."
        else:
            session["user"] = username
            session.permanent = request.form.get("ingat") == "on"  # centang "Ingat saya"
            return render_template("berhasil.html", judul="Login berhasil!",
                                   keterangan="Selamat datang, " + username + "!",
                                   tujuan=url_for("reservasi"), tombol="Masuk ke beranda")

    return render_template("masuk.html", pesan=pesan, aktif="masuk")


@app.route("/profil")
def profil():
    username = session["user"]
    data = users[username]
    lahir = datetime.strptime(data["lahir"], "%Y-%m-%d").date()
    hari_ini = date.today()
    umur = hari_ini.year - lahir.year - ((hari_ini.month, hari_ini.day) < (lahir.month, lahir.day))
    return render_template("profil.html", username=username,
                           lahir=lahir.strftime("%d-%m-%Y"), umur=umur,
                           gabung=data["gabung"], aktif="profil")


@app.route("/keluar")
def keluar():
    session.clear()
    return redirect(url_for("masuk"))

@app.route("/loker", methods=["GET", "POST"])
def loker():
    pesan = ""
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        pilihan = request.form.get("loker", "")

        if pilihan == "":
            pesan = "Pilih loker dulu ya!"
        elif pilihan not in lokers:
            pesan = "Loker tidak ditemukan."
        elif nama == "":
            pesan = "Isi nama dulu ya!"
        elif lokers[pilihan] is not None:
            pesan = "Maaf, loker " + pilihan + " sudah terpakai."
        else:
            lokers[pilihan] = nama
            kode = buat_kode("LKR")
            riwayat_loker.append({"kode": kode, "nama": nama, "loker": pilihan,
                                  "waktu": datetime.now().strftime("%d-%m-%Y %H:%M")})
            pesan = "Berhasil! Kunci loker " + pilihan + " dipinjam. Kode: " + kode

    terpakai = sum(1 for p in lokers.values() if p is not None)
    return render_template("loker.html", lokers=lokers, baris="ABCDEF",
                           terpakai=terpakai, total=len(lokers),
                           riwayat=riwayat_loker, pesan=pesan, aktif="loker")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)




























































