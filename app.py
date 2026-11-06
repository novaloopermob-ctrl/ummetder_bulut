import os
from flask import Flask, render_template_string, request, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Bulut veritabanı (DATABASE_URL) varsa onu kullan, yoksa yerel SQLite kullan
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn, 'postgres'
    else:
        conn = sqlite3.connect('butce_bulut.db')
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'

def init_db():
    conn, db_type = get_db()
    cursor = conn.cursor()
    if db_type == 'postgres':
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                            id SERIAL PRIMARY KEY,
                            tarih TEXT NOT NULL,
                            islem_tipi TEXT NOT NULL,
                            kategori TEXT NOT NULL,
                            tutar REAL NOT NULL,
                            aciklama TEXT)''')
    else:
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            tarih TEXT NOT NULL,
                            islem_tipi TEXT NOT NULL,
                            kategori TEXT NOT NULL,
                            tutar REAL NOT NULL,
                            aciklama TEXT)''')
    conn.commit()
    cursor.close()
    conn.close()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ortak Bulut Bütçe Defteri</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 15px; color: #333; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h2 { margin-top: 0; color: #2c3e50; text-align: center; }
        .cards { display: flex; gap: 10px; margin-bottom: 20px; }
        .card { flex: 1; background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; border: 1px solid #dee2e6; }
        .card h4 { margin: 0 0 5px 0; font-size: 14px; color: #6c757d; }
        .card p { margin: 0; font-size: 20px; font-weight: bold; }
        .income { color: #27ae60; }
        .expense { color: #c0392b; }
        form { background: #e9ecef; padding: 15px; border-radius: 6px; margin-bottom: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        form input, form select, form button { padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; width: 100%; box-sizing: border-box; }
        form button { background: #2c3e50; color: white; border: none; cursor: pointer; grid-column: span 2; font-weight: bold; }
        form button:hover { background: #34495e; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background: #f8f9fa; }
        .del-btn { color: #c0392b; text-decoration: none; font-weight: bold; }
        @media (max-width: 600px) { form { grid-template-columns: 1fr; } form button { grid-column: span 1; } }
    </style>
</head>
<body>
    <div class="container">
        <h2>📊 Ortak Bulut Bütçe & Kasa Defteri</h2>
        
        <div class="cards">
            <div class="card">
                <h4>Toplam Giren</h4>
                <p class="income">+{{ "%.2f"|format(toplam_gelir) }} TL</p>
            </div>
            <div class="card">
                <h4>Toplam Çıkan</h4>
                <p class="expense">-{{ "%.2f"|format(toplam_gider) }} TL</p>
            </div>
            <div class="card">
                <h4>Net Kasa / Kalan</h4>
                <p style="color: {{ '#27ae60' if net >= 0 else '#c0392b' }}">{{ "%.2f"|format(net) }} TL</p>
            </div>
        </div>

        <form action="/ekle" method="POST">
            <input type="date" name="tarih" value="{{ bugun }}" required>
            <select name="islem_tipi" required>
                <option value="Gelir">➕ Gelir (Para Girdi)</option>
                <option value="Gider">➖ Gider (Para Çıktı)</option>
            </select>
            <input type="text" name="kategori" placeholder="Kategori (Örn: Market, Akaryakıt)" required>
            <input type="number" step="0.01" name="tutar" placeholder="Tutar (TL)" required>
            <input type="text" name="aciklama" placeholder="Açıklama (İsteğe bağlı)" style="grid-column: span 2;">
            <button type="submit">İşlemi Kaydet</button>
        </form>

        <h3>Son İşlemler</h3>
        <table>
            <thead>
                <tr>
                    <th>Tarih</th>
                    <th>Tür</th>
                    <th>Kategori / Açıklama</th>
                    <th>Tutar</th>
                    <th>İşlem</th>
                </tr>
            </thead>
            <tbody>
                {% for row in islemler %}
                <tr>
                    <td>{{ row['tarih'] }}</td>
                    <td><span class="{{ 'income' if row['islem_tipi'] == 'Gelir' else 'expense' }}">{{ row['islem_tipi'] }}</span></td>
                    <td><b>{{ row['kategori'] }}</b><br><small style="color:#666;">{{ row['aciklama'] or '' }}</small></td>
                    <td class="{{ 'income' if row['islem_tipi'] == 'Gelir' else 'expense' }}">
                        {{ '+' if row['islem_tipi'] == 'Gelir' else '-' }}{{ "%.2f"|format(row['tutar']) }} TL
                    </td>
                    <td><a href="/sil/{{ row['id'] }}" class="del-btn" onclick="return confirm('Silmek istediğinize emin misiniz?');">Sil</a></td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="5" style="text-align: center; color: #888;">Henüz kayıt eklenmemiş.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    conn, db_type = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions ORDER BY tarih DESC, id DESC')
    islemler = cursor.fetchall()
    
    cursor.execute("SELECT SUM(tutar) FROM transactions WHERE islem_tipi = 'Gelir'")
    res_gelir = cursor.fetchone()
    toplam_gelir = (res_gelir['sum'] if db_type == 'postgres' else res_gelir[0]) or 0.0 if res_gelir else 0.0
    
    cursor.execute("SELECT SUM(tutar) FROM transactions WHERE islem_tipi = 'Gider'")
    res_gider = cursor.fetchone()
    toplam_gider = (res_gider['sum'] if db_type == 'postgres' else res_gider[0]) or 0.0 if res_gider else 0.0
    
    net = toplam_gelir - toplam_gider
    cursor.close()
    conn.close()
    
    bugun = datetime.now().strftime('%Y-%m-%d')
    return render_template_string(HTML_TEMPLATE, islemler=islemler, toplam_gelir=toplam_gelir, toplam_gider=toplam_gider, net=net, bugun=bugun)

@app.route('/ekle', methods=['POST'])
def ekle():
    tarih = request.form['tarih']
    islem_tipi = request.form['islem_tipi']
    kategori = request.form['kategori']
    tutar = float(request.form['tutar'])
    aciklama = request.form['aciklama']
    
    conn, _ = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO transactions (tarih, islem_tipi, kategori, tutar, aciklama) VALUES (%s, %s, %s, %s, %s)' if DATABASE_URL else 'INSERT INTO transactions (tarih, islem_tipi, kategori, tutar, aciklama) VALUES (?, ?, ?, ?, ?)',
                 (tarih, islem_tipi, kategori, tutar, aciklama))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/sil/<int:id>')
def sil(id):
    conn, _ = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = %s' if DATABASE_URL else 'DELETE FROM transactions WHERE id = ?', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
