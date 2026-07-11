Flow automation outlook:
menggunakan pywnin32 mengendalikan aplikasi desktop Microsoft Outlook secara langsung melalui COM (Component Object Model) dan mengambil session yang aktif dari akun tersebut. (tidak perlu credential/api/password)
di dalam tab automation outlook terdapat sub menu. rules engine, dan template.
# template
isinya adalah list list template yang dibuat oleh user, dan ada template yang memang default dari bawaannya aplikasi. menu template ini pure template, benar benar seperti fitur draft outlook.

- yang user bisa lakukan di menu template:
1. crud template (create new, edit, delete). ketika di klik add new template dan atau edit template, muncul side bar di kanan user yang akan tampilan seperti as is outlook ketika mengisi email/draft email(jadi tampilannya otomatis menjadi 50% list 50% area drafting template). tapi disini ada fitur place holder, bisa juga bodynya menggunakan HTML (tapi gw masih bingung, apakah kalau user pilih pake html, berarti harus upload file html dan area input body jadi gak bisa di edit. atau langsung ketik htmlnya di body atau bisa keduanya), fitur fitur input area menggunakan RTE engine yang sama di aplikasi ini yang ada seperti di menu project details, tapi di sesuaikan saja peruntukannya untuk menulis email/ draft email. ada fitur aplikasi dapat mengingat to/cc/bcc yang pernah digunakan di template. jadi misalkan ketika ketik huruf pertama s dan user pernah bikin template email dengan to/cc/bcc nya sayyidmibrahim@gmail.com, nanti dibawahnya ada suggestion gitu email sayyidmibrahim@gmail.com, dan user bisa langsung enter/tab untuk automatis menulis email tersebut. di template ini user juga harus memberi nama template ini, dan kategorinya (send new email / reply email), user juga bisa kasih hastag custom. agar nanti ada fitur search template dan filtering template untuk memudahkan user mencari dan mengelola template email outlooknya. ketika selesai edit draft/tempaltenya, user bisa klik save (ketika klik save, tampilan side bar untuk edit tempaltenya otomatis tertutup), button untuk liat hasilnya langsung di outlooknya, dan button create rules untuk membuat rules dari tempalte ini.
2. Mengelola, mencari template template menggunakan fitur search dan atau filtering yang pintar
3. di tiap list template terdapat info juga kalau template ini sudah terattach/belum dengan rules. jadi keliatan mana tempalate yang sudah terattach / dipakai rules mana yang belum ketika cursor di hover ke area list tersebut.

# Rules Engine
isinya adalah rules rules automations outlook yang pernah di buat, yang aktif maupun yang tidak aktif. rules ini berdasarkan goal centric, yang berarti ketika user klik new addrules, user harus pilih goalsnya terlebih dahulu (send new email/ reply email/ download email/ auto update status CR) dan settingan rules mengikuti goals yang di pilih user.tampilan yang gw bayangin kalau rules masih kosong itu ada space buat nantinya berisi rules rules yang udh di buat, ada button add rules, filtering rules, search rules, dan ada button log, yang kalau di klik dia akan muncul side bar kanan berisi log log rules yang aktif, yang berjalan, next rulesnya apa, hasil eksekusi tiap rulesnya di tampilin lognya dengan detail dan lengkap tapi dengan format yang nyaman di baca oleh user penjelasan dari lognya. formatnya 01 January 2025, hh:mm:ss.ms [INFO] Message -> ini fomrat log aplikasi ini di semua log aplikasi ini harus seperti ini formatnya. dan ketika tombol log itu di pencet lagi, side bar otomatis akan tertutup gitu.
dan ditiap list pun ada button log, yang ketika di klik akan tampil log khusus rules itu, dengan sidebar kanan yang sama perisis seperti log global rules.
yang user bisa lakukan di menu rules engine:
1. curd (create new, edit, delete). flownya new rules: user klik new rules -> pilih goals -> isi settingnya -> done
2. mengelola, mencari, memantau aktifitas seluruh rules
3. di tiap rules juga ada settingan on atau off untuk mengaktifkan dan mematikan rules tersebut
details settingan tiap goals:
1. Send New Email
- isi nama rules -> isi goals Send New Email -> isi hastag (optional)
- Trigger: 
1. Manual Trigger -> harus di jalankan dengan cara klik tombol run di rulesnya langsung
1.1. Chose template -> pililh hanya 1 template 
1.2. 

2. Schedule -> by scheduler (aplikasi harus bisa deteksi kalau oulook user menggunakan outlook classic harus ada info gitu kalau scheduler hanya jalan jika lapotp dan outlooknya nyala, karena masih pakai metode delay delivery, dan kalau udh pake outlook new dengan schedule send kasih info juga email bakal terkirim walau laptop mati.)
2.1. pilih template -> pilih hanya 1 template

3. On CR Condition -> berdasarkan beberapa pattern dari data data CR (CR Type, appcode, project type atau spesifik CR)
