
import os, sqlite3, logging, time
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
from contextlib import contextmanager
from telegram import Update, InlineKeyboardButton as B, InlineKeyboardMarkup as M, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler

logging.basicConfig(level=logging.INFO)
TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
ADMINS={int(x.strip()) for x in os.getenv("ADMIN_TELEGRAM_IDS","8750836528,6855869223").split(",") if x.strip().isdigit()}
DB=os.getenv("DATABASE_PATH","kh_shop.db")
CATEGORIES=["⭐ Telegram Stars","🎁 Telegram Gifts","💎 NFT","💠 TON","🎬 GIF","➕ Boshqa"]
TITLE,PRICE,DESCRIPTION,CARD,RECEIPT=range(5)

@contextmanager
def db():
    Path(DB).parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(DB,timeout=20)
    con.row_factory=sqlite3.Row
    try:
        yield con
        con.commit()
    finally: con.close()

def init():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,category TEXT NOT NULL,title TEXT NOT NULL,price INTEGER NOT NULL,description TEXT NOT NULL,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS cards(id INTEGER PRIMARY KEY,details TEXT NOT NULL,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,username TEXT,product_id INTEGER,title TEXT NOT NULL,amount INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'awaiting_payment',receipt_file_id TEXT,created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS cart(user_id INTEGER NOT NULL,product_id INTEGER NOT NULL,PRIMARY KEY(user_id,product_id));
        """)

def kb(rows): return M([[B(text,callback_data=data) for text,data in row] for row in rows])
def menu(admin=False):
    rows=[["🛍 Katalog","🛒 Savat"],["📦 Buyurtmalarim","ℹ️ Yordam"]]
    if admin: rows.append(["👑 Admin panel"])
    return ReplyKeyboardMarkup(rows,resize_keyboard=True)
def is_admin(u): return u and u.id in ADMINS

async def start(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    admin=is_admin(update.effective_user)
    await update.message.reply_text("👑 KH SHOP admin paneliga xush kelibsiz!" if admin else "🛍 KH SHOP ga xush kelibsiz!",reply_markup=menu(admin))
    if admin: await admin_panel(update,ctx)

async def admin_panel(update,ctx):
    if not is_admin(update.effective_user): return
    rows=[[("➕ Mahsulot qo‘shish","a:add")],[("📋 Mahsulotlarni boshqarish","a:products")],[("💳 Karta qo‘shish","a:card")],[("🗑 Kartalarni boshqarish","a:cards")],[("📥 Buyurtmalar","a:orders")],[("📊 Statistika","a:stats")]]
    await update.effective_message.reply_text("👑 Admin boshqaruvi",reply_markup=kb(rows))

async def catalog(update,ctx):
    rows=[[(cat,f"cat:{i}")] for i,cat in enumerate(CATEGORIES)]
    await update.effective_message.reply_text("🛍 Kategoriyani tanlang:",reply_markup=kb(rows))

async def cart(update,ctx):
    uid=update.effective_user.id
    with db() as c:
        items=c.execute("SELECT p.* FROM cart x JOIN products p ON p.id=x.product_id WHERE x.user_id=? AND p.active=1",(uid,)).fetchall()
    if not items: await update.effective_message.reply_text("🛒 Savat bo‘sh.");return
    rows=[[(f"{p['title']} — {p['price']:,} so‘m",f"buy:{p['id']}"),("❌",f"remove:{p['id']}")] for p in items]
    await update.effective_message.reply_text("🛒 Savatdagi mahsulotlar (xarid uchun mahsulotni tanlang):",reply_markup=kb(rows))

async def orders(update,ctx):
    uid=update.effective_user.id
    with db() as c: rows=c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 15",(uid,)).fetchall()
    if not rows: await update.effective_message.reply_text("Hali buyurtmangiz yo‘q.");return
    await update.effective_message.reply_text("\n".join(f"#{r['id']} · {r['title']} · {r['amount']:,} so‘m · {r['status']}" for r in rows))

async def text_menu(update,ctx):
    t=update.message.text
    if t=="🛍 Katalog": await catalog(update,ctx)
    elif t=="🛒 Savat": await cart(update,ctx)
    elif t=="📦 Buyurtmalarim": await orders(update,ctx)
    elif t=="👑 Admin panel": await admin_panel(update,ctx)
    elif t=="ℹ️ Yordam": await update.message.reply_text("Mahsulot tanlang, savatga qo‘shing va buyurtma bering. To‘lov faqat bot ko‘rsatgan ruxsat etilgan usulda amalga oshiriladi. Muammo bo‘lsa admin bilan bog‘laning.")
    else: await update.message.reply_text("Menyudan tugmani tanlang.",reply_markup=menu(is_admin(update.effective_user)))

async def callback(update,ctx):
    q=update.callback_query; await q.answer()
    u=update.effective_user; data=q.data
    if data.startswith("cat:"):
        i=int(data.split(":")[1]); cat=CATEGORIES[i]
        with db() as c: rows=c.execute("SELECT * FROM products WHERE category=? AND active=1",(cat,)).fetchall()
        if not rows: await q.message.reply_text("Bu kategoriyada hozircha mahsulot yo‘q.");return
        await q.message.reply_text(cat,reply_markup=kb([[(f"{p['title']} — {p['price']:,} so‘m",f"p:{p['id']}")] for p in rows]))
    elif data.startswith("p:"):
        pid=int(data[2:])
        with db() as c: p=c.execute("SELECT * FROM products WHERE id=? AND active=1",(pid,)).fetchone()
        if p: await q.message.reply_text(f"{p['title']}\n{p['description']}\nNarx: {p['price']:,} so‘m",reply_markup=kb([[("🛒 Savatga",f"add:{pid}"),("🧾 Buyurtma",f"buy:{pid}")]]))
    elif data.startswith("add:"):
        pid=int(data[4:])
        with db() as c: c.execute("INSERT OR IGNORE INTO cart VALUES (?,?)",(u.id,pid))
        await q.message.reply_text("✅ Savatga qo‘shildi.")
    elif data.startswith("remove:"):
        with db() as c: c.execute("DELETE FROM cart WHERE user_id=? AND product_id=?",(u.id,int(data[7:])))
        await q.message.reply_text("Savatdan olib tashlandi.")
    elif data.startswith("buy:"):
        pid=int(data[4:])
        with db() as c:
            p=c.execute("SELECT * FROM products WHERE id=? AND active=1",(pid,)).fetchone()
            if not p: await q.message.reply_text("Mahsulot mavjud emas.");return
            cur=c.execute("INSERT INTO orders(user_id,username,product_id,title,amount,created_at) VALUES (?,?,?,?,?,?)",(u.id,u.username or "",pid,p["title"],p["price"],int(time.time())))
            oid=cur.lastrowid
            cards=c.execute("SELECT details FROM cards WHERE active=1").fetchall()
        # No card-based payment instructions for Telegram digital goods: Telegram Stars payment must be integrated via official invoice flow.
        await q.message.reply_text(f"🧾 Buyurtma #{oid} yaratildi.\nMahsulot: {p['title']}\nNarx: {p['price']:,} so‘m.\n\n⚠️ Telegram ichidagi raqamli mahsulotlar uchun to‘lovni Telegram Stars rasmiy invoice tizimiga ulash zarur. Hozir buyurtma faqat admin ko‘rishi uchun qayd etildi; pul yubormang.")
        await notify_admins(ctx,f"🆕 Buyurtma #{oid}\nXaridor: {u.id} @{u.username or '-'}\n{p['title']}\nNarx: {p['price']:,} so‘m\nHolat: awaiting_payment",oid)
    elif data.startswith("a:") or data.startswith("adm:"):
        if not is_admin(u): return
        await admin_callback(q,ctx,data)
    elif data.startswith("status:"):
        if not is_admin(u):return
        _,oid,st=data.split(":")
        if st not in ("approved","rejected","delivered"):return
        with db() as c:
            row=c.execute("SELECT * FROM orders WHERE id=?",(int(oid),)).fetchone()
            if not row:return
            if st=="delivered" and row["status"]!="approved": await q.message.reply_text("Avval tasdiqlang.");return
            c.execute("UPDATE orders SET status=? WHERE id=?",(st,int(oid)))
        await q.message.reply_text(f"Buyurtma #{oid}: {st}")
        try: await ctx.bot.send_message(row["user_id"],f"📦 Buyurtma #{oid} holati: {st}")
        except Exception: logging.exception("User notification failed")

async def notify_admins(ctx,message,oid):
    for aid in ADMINS:
        try: await ctx.bot.send_message(aid,message,reply_markup=kb([[("📄 Ko‘rish",f"adm:order:{oid}")]]))
        except Exception: logging.exception("Admin notification failed")

async def admin_callback(q,ctx,data):
    parts=data.split(":")
    action=parts[1]
    if action=="add":
        await q.message.reply_text("Mahsulot kategoriyasini tanlang:",reply_markup=kb([[(cat,f"adm:newcat:{i}")] for i,cat in enumerate(CATEGORIES)]))
    elif action=="newcat":
        ctx.user_data["new_product"]={"category":CATEGORIES[int(parts[2])]}
        ctx.user_data["step"]="title"
        await q.message.reply_text("Mahsulot nomini yuboring. Bekor qilish: /cancel")
    elif action=="card":
        ctx.user_data["step"]="card"
        await q.message.reply_text("Karta ma’lumotini yuboring (faqat qonuniy, Telegram qoidalariga mos tashqi to‘lovlar uchun). /cancel")
    elif action=="products":
        with db() as c: rows=c.execute("SELECT * FROM products ORDER BY id DESC LIMIT 40").fetchall()
        await q.message.reply_text("Mahsulotlar:",reply_markup=kb([[(f"#{r['id']} {r['title']} ({'faol' if r['active'] else 'o‘chiq'})",f"adm:toggle:{r['id']}")] for r in rows]) if rows else None)
        if not rows: await q.message.reply_text("Mahsulot yo‘q.")
    elif action=="toggle":
        with db() as c: c.execute("UPDATE products SET active=1-active WHERE id=?",(int(parts[2]),))
        await q.message.reply_text("Mahsulot faolligi o‘zgartirildi.")
    elif action=="cards":
        with db() as c: rows=c.execute("SELECT * FROM cards ORDER BY id DESC").fetchall()
        if rows: await q.message.reply_text("Kartalar (bosib yoqing/o‘chiring):",reply_markup=kb([[(f"#{r['id']} {r['details'][:25]} {'✅' if r['active'] else '❌'}",f"adm:togglecard:{r['id']}")] for r in rows]))
        else: await q.message.reply_text("Karta yo‘q.")
    elif action=="togglecard":
        with db() as c: c.execute("UPDATE cards SET active=1-active WHERE id=?",(int(parts[2]),))
        await q.message.reply_text("Karta holati o‘zgardi.")
    elif action=="orders":
        with db() as c: rows=c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 30").fetchall()
        if rows: await q.message.reply_text("Buyurtmalar:",reply_markup=kb([[(f"#{r['id']} {r['title']} · {r['status']}",f"adm:order:{r['id']}")] for r in rows]))
        else: await q.message.reply_text("Buyurtma yo‘q.")
    elif action=="order":
        with db() as c: r=c.execute("SELECT * FROM orders WHERE id=?",(int(parts[2]),)).fetchone()
        if r:
            await q.message.reply_text(f"#{r['id']}\nXaridor ID: {r['user_id']}\n@{r['username']}\n{r['title']}\n{r['amount']:,} so‘m\nHolat: {r['status']}\nChek: {'bor' if r['receipt_file_id'] else 'yo‘q'}",reply_markup=kb([[("✅ Tasdiqlash",f"status:{r['id']}:approved"),("❌ Rad",f"status:{r['id']}:rejected")],[("📦 Yetkazildi",f"status:{r['id']}:delivered")]]))
            if r["receipt_file_id"]:
                try: await ctx.bot.send_photo(q.message.chat_id,r["receipt_file_id"])
                except Exception: pass
    elif action=="stats":
        with db() as c:
            n=c.execute("SELECT count(*) FROM orders").fetchone()[0]
            done=c.execute("SELECT count(*) FROM orders WHERE status='delivered'").fetchone()[0]
            products=c.execute("SELECT count(*) FROM products WHERE active=1").fetchone()[0]
        await q.message.reply_text(f"📊 Buyurtmalar: {n}\nYetkazilgan: {done}\nFaol mahsulotlar: {products}")

async def admin_input(update,ctx):
    if not is_admin(update.effective_user):return False
    step=ctx.user_data.get("step")
    if not step:return False
    value=update.message.text.strip()
    if step=="title":
        if len(value)>100: await update.message.reply_text("Nom juda uzun.");return True
        ctx.user_data["new_product"]["title"]=value;ctx.user_data["step"]="price"
        await update.message.reply_text("Narxni so‘mda butun son bilan kiriting:")
    elif step=="price":
        if not value.isdigit() or int(value)<1: await update.message.reply_text("Musbat butun son kiriting.");return True
        ctx.user_data["new_product"]["price"]=int(value);ctx.user_data["step"]="description"
        await update.message.reply_text("Mahsulot tavsifini kiriting:")
    elif step=="description":
        p=ctx.user_data["new_product"]
        with db() as c: c.execute("INSERT INTO products(category,title,price,description) VALUES (?,?,?,?)",(p["category"],p["title"],p["price"],value[:2000]))
        ctx.user_data.pop("step",None);ctx.user_data.pop("new_product",None)
        await update.message.reply_text("✅ Mahsulot qo‘shildi.")
    elif step=="card":
        with db() as c: c.execute("INSERT INTO cards(details) VALUES (?)",(value[:200],))
        ctx.user_data.pop("step",None)
        await update.message.reply_text("Karta ma’lumoti saqlandi. Eslatma: raqamli mahsulotlarni Telegram ichida sotish uchun Stars invoice kerak.")
    return True

async def receipt(update,ctx):
    # Receipt can be associated with the latest order; not proof of payment.
    uid=update.effective_user.id
    with db() as c:
        row=c.execute("SELECT * FROM orders WHERE user_id=? AND status='awaiting_payment' ORDER BY id DESC LIMIT 1",(uid,)).fetchone()
        if not row: await update.message.reply_text("Chek biriktirish uchun kutilayotgan buyurtma yo‘q.");return
        fid=update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
        c.execute("UPDATE orders SET receipt_file_id=?,status='receipt_review' WHERE id=?",(fid,row["id"]))
    await update.message.reply_text(f"🧾 Chek buyurtma #{row['id']} ga biriktirildi. Bu avtomatik to‘lov tasdig‘i emas.")
    for aid in ADMINS:
        try:
            await ctx.bot.send_message(aid,f"🧾 Buyurtma #{row['id']} uchun chek. Bank orqali mustaqil tekshiring.")
            await ctx.bot.send_photo(aid,fid) if update.message.photo else await ctx.bot.send_document(aid,fid)
            await ctx.bot.send_message(aid,"Buyurtma:",reply_markup=kb([[("Tekshirish",f"adm:order:{row['id']}")]]))
        except Exception: logging.exception("Receipt forwarding failed")

async def message(update,ctx):
    if await admin_input(update,ctx):return
    await text_menu(update,ctx)

async def cancel(update,ctx):
    ctx.user_data.clear()
    await update.message.reply_text("Amal bekor qilindi.",reply_markup=menu(is_admin(update.effective_user)))

def main():
    if not TOKEN: raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable required")
    init()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("cancel",cancel))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE,receipt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,message))
    # Render Free Web Service: Telegram webhook and HTTP listener.
    base_url = (os.getenv("WEBHOOK_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL", "")).rstrip("/")
    if not base_url:
        raise RuntimeError("RENDER_EXTERNAL_URL topilmadi. Render Web Service URL manzilini WEBHOOK_BASE_URL sifatida kiriting.")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        url_path="telegram",
        webhook_url=f"{base_url}/telegram",
        drop_pending_updates=False,
    )

if __name__=="__main__": main()
