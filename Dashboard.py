from flask import Flask, render_template, redirect, url_for, request
import pandas as pd
import plotly.express as px
import plotly.io as pio
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import os

app=Flask(__name__,template_folder='./template')


############################################### CONFIGURAR BANCO
    
db_config = {
    'host': 'localhost',            # SEU HOST 
    'user': '',                     # SEu USUÁRIO
    'password': '',                 # SUA SENHA
    'database': 'dados_dashboard',  # NOME DO BANCO CRIADO
    'port': 3306                    # PORTA PADRÃO, MUDE CASO NECESSÁRIO
}

################################################################

def create_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
    return None

def fetch_data(query, params=None):
    """Executa uma consulta SQL e retorna um DataFrame com os resultados."""
    connection = create_connection()
    if connection:
        try:
            df = pd.read_sql(query, connection, params=params)
        except Error as e:
            print(f"Erro ao executar consulta: {e}")
            df = pd.DataFrame()
        finally:
            connection.close()
    else:
        df = pd.DataFrame()
    return df

def generate_data_html(df, actual_date):
    """Gera o HTML para a tabela de dados com base na data fornecida."""
    rows_html = ""
    for _, row in df.iterrows():
        # Certifique-se de que row['dataUltimaConexao'] é um datetime.date
        row_date = row['dataUltimaConexao'].date() if isinstance(row['dataUltimaConexao'], pd.Timestamp) else row['dataUltimaConexao']
        date_class = "bg-warning" if row_date != actual_date else ""
        
        # Formatar horaUltimaconexao
        if isinstance(row['horaUltimaconexao'], pd.Timedelta):
            hora_formatada = str(row['horaUltimaconexao']).split(' ')[-1]  # Extrai o tempo no formato HH:MM:SS
        else:
            hora_formatada = row['horaUltimaconexao']  # Presume que já está em formato correto
        
        row_html = f"""
        <tr class="{date_class}">
            <td>{row['modeloEquip']}</td>
            <td>{row['numSerieEquip']}</td>
            <td>{row['ipEquip']}</td>
            <td>{row['portaEquip']}</td>
            <td>{row['statusEquip']}</td>
            <td>{row['dataUltimaConexao']}</td>
            <td>{hora_formatada}</td>
            <td>{row['dataUltimoRegistro']}</td>
        </tr>
        """
        rows_html += row_html

    data_html = f"""
    <table class="table table-striped table-bordered">
        <thead>
            <tr>
                <th>Modelo do equipamento</th>
                <th>N° de série do equipamento</th>
                <th>Endereço IP</th>
                <th>Porta</th>
                <th>Status</th>
                <th>Data da última conexão</th>
                <th>Hora da última conexão</th>
                <th>Data do último tráfego</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """
    return data_html

@app.route('/')
def index():
    
    ############################################### VARIÁVEIS IMPORTANTES
    
    selected_date = request.args.get('selected_date', default=pd.Timestamp.now().strftime('%Y-%m-%d'), type=str)
    actual_date = pd.to_datetime(selected_date).date()
    previous_date = actual_date - timedelta(days=1)
    
    actual_date_day = actual_date.day
    actual_date_month = actual_date.month
    actual_date_year = actual_date.year
    
    previous_date_day = previous_date.day
    previous_date_month = previous_date.month
    
    formatted_actual_day_month = f"{actual_date_day:02d}/{actual_date_month:02d}"
    formatted_actual_complete = f"{actual_date_day:02d}/{actual_date_month:02d}/{actual_date_year}"
    
    formatted_previous_day_month = f"{previous_date_day:02d}/{previous_date_month:02d}"
    
    ############################################### GERAÇÃO DE DADOS GERAL
    geral_query = """
    SELECT modeloEquip, numSerieEquip, ipEquip, portaEquip, statusEquip, dataUltimaConexao, horaUltimaconexao, dataUltimoRegistro
    FROM dados
    WHERE criacaoInsert = %s
    ORDER BY dataUltimaConexao DESC, horaUltimaconexao DESC, dataUltimoRegistro DESC
    """
    geral_params = (actual_date,)
    df = fetch_data(geral_query, params=geral_params)

    total_equipamentos = fetch_data("""
    SELECT COUNT(*) AS equipsCadastrados
    FROM dados
    WHERE criacaoInsert = %s
    """, params=geral_params).iloc[0]['equipsCadastrados']

    conectados = fetch_data("""
    SELECT COUNT(*) AS equipsConectados
    FROM dados
    WHERE statusEquip = 'Conectado' AND criacaoInsert = %s
    """, params=geral_params).iloc[0]['equipsConectados']

    desconectados = fetch_data("""
    SELECT COUNT(*) AS equipsDesconectados
    FROM dados
    WHERE statusEquip = 'Desconectado' AND criacaoInsert = %s
    """, params=geral_params).iloc[0]['equipsDesconectados']

    color_map_geral = {
        'Conectado': '#0f6636',
        'Desconectado': '#dcdcdc'
    }

    fig_all = px.pie(
        df,
        names='statusEquip',
        title='Geral - Conectados x Desconectados',
        color='statusEquip',
        color_discrete_map=color_map_geral,
    )

    fig_all.update_traces(textfont_size=30)             # Ajusta o tamanho da fonte dos valores
    fig_all.update_layout(title_font_size=22)           # Ajusta o tamanho da fonte do título
    fig_all.update_layout(legend_title_font_size=12)    # Ajusta o tamanho da fonte da legenda
    fig_all.update_layout(legend_font_size=12)          # Ajusta o tamanho da caixa da legenda
    fig_all.update_layout(title_x=0.5)                  # Centraliza o título horizontalmente
    fig_all.update_layout(
        legend_title_font_size=12,  # Ajusta o tamanho do título da legenda
        legend_font_size=12,        # Ajusta o tamanho do texto da legenda
        legend_orientation="h",     # Muda a orientação da legenda para horizontal
        legend_yanchor="top",       # Alinha a legenda ao topo da posição y
        legend_y=-0.2,              # Ajuste a posição vertical da legenda para baixo
        legend_x=0.5,               # Centraliza a legenda horizontalmente
        legend_xanchor="center",    # Alinha a legenda ao centro da posição x
    )
    
    graph_html_all = pio.to_html(fig_all, full_html=False)  # Converter o gráfico para HTML
    
    
    
    ############################################### GERAÇÃO DE DADOS DO DIA ATUAL
    
    dia_atual_query = """
    SELECT modeloEquip, numSerieEquip, ipEquip, portaEquip, statusEquip, dataUltimaConexao, horaUltimaconexao, dataUltimoRegistro
    FROM dados
    WHERE dataUltimaConexao = %s
    ORDER BY dataUltimaConexao DESC, horaUltimaconexao DESC
    """
    df_today = fetch_data(dia_atual_query, params=(actual_date,))
    
    color_map_today = {
        'Conectado': '#0f6636',
        'Desconectado': '#dcdcdc'
    }

    total_today = fetch_data("""
    SELECT COUNT(*) AS 'equipsMovimentacao'
    FROM dados
    WHERE dataUltimaConexao = %s
    """, params=(actual_date,)).iloc[0]['equipsMovimentacao']

    conectados_today = fetch_data("""
    SELECT COUNT(*) AS 'equipsConectados'
    FROM dados
    WHERE statusEquip = 'Conectado' AND dataUltimaConexao = %s
    """, params=(actual_date,)).iloc[0]['equipsConectados']

    desconectados_today = fetch_data("""
    SELECT COUNT(*) AS 'equipsDesconectados'
    FROM dados
    WHERE statusEquip = 'Desconectado' AND dataUltimaConexao = %s 
    """, params=(actual_date,)).iloc[0]['equipsDesconectados']

    fig_today = px.pie(
        df_today,
        names='statusEquip',
        title=f'Conectados x Desconectados em {formatted_actual_complete}',
        color='statusEquip',
        color_discrete_map=color_map_today,
    )

    fig_today.update_traces(textfont_size=30)               # Ajusta o tamanho da fonte dos valores
    fig_today.update_layout(title_font_size=22)             # Ajusta o tamanho da fonte do título
    fig_today.update_layout(legend_title_font_size=12)      # Ajusta o tamanho da fonte da legenda
    fig_today.update_layout(legend_font_size=12)            # Ajusta o tamanho da caixa da legenda
    fig_today.update_layout(title_x=0.5)                    # Centraliza o título horizontalmente
    fig_today.update_layout(
        legend_title_font_size=12,  # Ajusta o tamanho do título da legenda
        legend_font_size=12,        # Ajusta o tamanho do texto da legenda
        legend_orientation="h",     # Muda a orientação da legenda para horizontal
        legend_yanchor="top",       # Alinha a legenda ao topo da posição y
        legend_y=-0.2,              # Ajuste a posição vertical da legenda para baixo
        legend_x=0.5,               # Centraliza a legenda horizontalmente
        legend_xanchor="center",    # Alinha a legenda ao centro da posição x
    )

    # Converter o gráfico para HTML
    graph_html_today = pio.to_html(fig_today, full_html=False)
    
    ############################################### GERAÇÃO DE DADOS DE EQUIPAMENTOS QUE TRAFEGARAM

    # Consulta SQL para equipamentos que trafegaram hoje ou ontem
    trafego_query = """
    SELECT 
        modeloEquip, numSerieEquip, ipEquip, portaEquip, statusEquip, 
        dataUltimaConexao, horaUltimaConexao, dataUltimoRegistro
    FROM dados
    WHERE dataUltimoRegistro IN (%s, %s)
    ORDER BY dataUltimaConexao DESC, horaUltimaConexao DESC, dataUltimoRegistro DESC
    """ % (f"'{actual_date}'", f"'{previous_date}'")

    df_trafego = fetch_data(trafego_query)
    
    color_map_trafego = {
        'Com Tráfego Recente': '#0f6636',
        'Sem Tráfego Recente': '#dcdcdc'
    }
    
    # Contar ttoal de equips
    total_equips_trafego = fetch_data("""
    SELECT COUNT(*) AS 'totalEquipamentos'
    FROM dados
    WHERE dataUltimaConexao = %s AND dataUltimoRegistro <= %s
    """, params=(actual_date,actual_date,)).iloc[0]['totalEquipamentos']
    
    total_trafegaram_recente = fetch_data("""
    SELECT COUNT(*) AS 'equipsTrafegaramRecente' 
    FROM dados 
    WHERE dataUltimaConexao = %s AND (dataUltimoRegistro = %s OR dataUltimoRegistro = %s)
    """, params=(actual_date,actual_date, previous_date,)).iloc[0]['equipsTrafegaramRecente']

    nao_trafegaram_recentemente = total_equips_trafego - total_trafegaram_recente

    # Criar o gráfico
    fig_travel = px.pie(
        df_trafego,
        names=['Com Tráfego Recente', 'Sem Tráfego Recente'],
        values=[total_trafegaram_recente, nao_trafegaram_recentemente],
        title=f'Tráfego de Equipamentos em {formatted_actual_complete}',
        color=['Com Tráfego Recente', 'Sem Tráfego Recente'],
        color_discrete_map=color_map_trafego,  # Usando color_map_trafego aqui
    )

    # Atualizar o gráfico
    fig_travel.update_traces(textfont_size=30)              # Ajusta o tamanho da fonte dos valores 
    fig_travel.update_layout(title_font_size=22)            # Ajusta o tamanho da fonte do título
    fig_travel.update_layout(legend_title_font_size=12)     # Ajusta o tamanho da fonte da legenda
    fig_travel.update_layout(legend_font_size=12)           # Ajusta o tamanho da caixa da legenda
    fig_travel.update_layout(title_x=0.5)                   # Centraliza o título horizontalmente
    fig_travel.update_layout(
        legend_title_font_size=12,  # Ajusta o tamanho do título da legenda
        legend_font_size=12,        # Ajusta o tamanho do texto da legenda
        legend_orientation="h",     # Muda a orientação da legenda para horizontal
        legend_yanchor="top",       # Alinha a legenda ao topo da posição y
        legend_y=-0.2,              # Ajuste a posição vertical da legenda para baixo
        legend_x=0.5,               # Centraliza a legenda horizontalmente
        legend_xanchor="center",    # Alinha a legenda ao centro da posição x
    )
    graph_html_travel = pio.to_html(fig_travel, full_html=False)

    data_html = generate_data_html(df, actual_date)

    return render_template('index.html',
                           graph_html_all=graph_html_all,
                           graph_html_today=graph_html_today,
                           graph_html_travel=graph_html_travel,
                           data_html=data_html,
                           total_equipamentos=total_equipamentos,
                           conectados=conectados,
                           desconectados=desconectados,
                           total_today=total_today,
                           conectados_today=conectados_today,
                           desconectados_today=desconectados_today,
                           total_equips_trafego=total_equips_trafego,
                           total_trafegaram_recente=total_trafegaram_recente,
                           nao_trafegaram_recentemente=nao_trafegaram_recentemente,
                           formatted_actual_day_month=formatted_actual_day_month,
                           formatted_previous_day_month=formatted_previous_day_month,
                           formatted_actual_complete=formatted_actual_complete)

@app.route('/update_date', methods=['POST'])
def update_date():
    selected_date = request.form.get('date')
    return redirect(url_for('index', selected_date=selected_date))


@app.route('/dashboard-mensal')
def dashboard_mensal():
    # Obter o mês e ano a partir dos parâmetros da URL
    selected_month = request.args.get('month', default=pd.Timestamp.now().strftime('%Y-%m'), type=str)
    
    # Converter o mês selecionado para ano e mês
    year, month = map(int, selected_month.split('-'))

    # Consultas SQL para os dados diários do mês selecionado
    geral_query = """
    SELECT modeloEquip, numSerieEquip, ipEquip, portaEquip, statusEquip, dataUltimaConexao, horaUltimaconexao, dataUltimoRegistro
    FROM dados
    WHERE criacaoInsert = CURDATE()
    ORDER BY dataUltimaConexao DESC, horaUltimaconexao DESC, dataUltimoRegistro DESC
    """
    df = fetch_data(geral_query)
    
    
    movimentacao_query = """
    SELECT DATE(criacaoInsert) AS day, COUNT(*) AS equipsMovimentacao
    FROM dados
    WHERE YEAR(criacaoInsert) = %s AND MONTH(criacaoInsert) = %s
    GROUP BY day
    ORDER BY day
    """
    
    conectados_query = """
    SELECT DATE(criacaoInsert) AS day, COUNT(*) AS equipsConectados
    FROM dados
    WHERE statusEquip = 'Conectado' AND YEAR(criacaoInsert) = %s AND MONTH(criacaoInsert) = %s
    GROUP BY day
    ORDER BY day
    """
    
    desconectados_query = """
    SELECT DATE(criacaoInsert) AS day, COUNT(*) AS equipsDesconectados
    FROM dados
    WHERE statusEquip = 'Desconectado' AND YEAR(criacaoInsert) = %s AND MONTH(criacaoInsert) = %s
    GROUP BY day
    ORDER BY day
    """
    
    media_cadastrados_query = """
    SELECT FLOOR(AVG(equipsMovimentacao)) AS mediaEquipsMovimentacao
    FROM (
        SELECT criacaoInsert, COUNT(*) AS equipsMovimentacao
        FROM dados
        GROUP BY criacaoInsert
    ) AS mediaMovimentacao
    WHERE YEAR(criacaoInsert) = %s AND MONTH(criacaoInsert) = %s
    """
    
    media_conectados_query = """
    SELECT FLOOR(AVG(equipsConectados)) AS mediaEquipsConectados
    FROM (
        SELECT criacaoInsert, COUNT(*) AS equipsConectados
        FROM dados
        WHERE statusEquip = 'Conectado'
        GROUP BY criacaoInsert
    ) AS mediaConectados
    WHERE YEAR(criacaoInsert) = %s AND MONTH(criacaoInsert) = %s
    """
    
    media_desconectados_query = """
    SELECT FLOOR(AVG(equipsDesconectados)) AS mediaEquipsDesconectados
    FROM (
        SELECT criacaoInsert, COUNT(*) AS equipsDesconectados
        FROM dados
        WHERE statusEquip = 'Desconectado'
        GROUP BY criacaoInsert
    ) AS mediaDesconectados
    WHERE YEAR(criacaoInsert) = %s AND MONTH(criacaoInsert) = %s
    """

    # Buscar dados
    df_movimentacao = fetch_data(movimentacao_query, params=(year, month))
    df_conectados = fetch_data(conectados_query, params=(year, month))
    df_desconectados = fetch_data(desconectados_query, params=(year, month))
    
    # Consultar as médias
    media_cadastrados_df = fetch_data(media_cadastrados_query, params=(year, month))
    media_cadastrados = media_cadastrados_df.iloc[0]['mediaEquipsMovimentacao']
    
    media_conectados_df = fetch_data(media_conectados_query, params=(year, month))
    media_conectados = media_conectados_df.iloc[0]['mediaEquipsConectados']
    
    media_desconectados_df = fetch_data(media_desconectados_query, params=(year, month))
    media_desconectados = media_desconectados_df.iloc[0]['mediaEquipsDesconectados']
    

    
    # Preparar os dados para o gráfico
    df_combined = pd.merge(df_movimentacao, df_conectados, on='day', how='left', suffixes=('_total', '_conectados'))
    df_combined = pd.merge(df_combined, df_desconectados, on='day', how='left')
    df_combined.rename(columns={'day': 'Data', 'equipsMovimentacao': 'Cadastrados', 'equipsConectados': 'Conectados', 'equipsDesconectados': 'Desconectados'}, inplace=True)
    
    color_map_mensal = {
    # 'Cadastrados': '#808080',
    'Cadastrados': '#2180de',
    'Conectados': '#1bb15e',
    'Desconectados': '#de2121'
    }  

    # Criar o gráfico linear
    fig = px.line(
        df_combined,
        x='Data',
        y=['Cadastrados', 'Conectados', 'Desconectados'],
        labels={'value': 'Quantidade', 'Data': 'Data'},
        title='Movimentação de Equipamentos por Dia',
        markers=True,
        color_discrete_map=color_map_mensal,
    )
    
    fig.update_layout(
        title_font_size=22,             # Define o tamanho da fonte do título
        xaxis_title='Data',             # Define um título para os dados do eixo X
        yaxis_title='Quantidade',       # Define um título para os dados do eixo Y
        legend_title='Legenda',         # Define o título da legenda
        legend_title_font_size=12,      # Define o tamanho da fonte to título da legenda
        legend_font_size=12,            # Define o tamanho da fonte da legenda
        title_x=0.5,                    # ?
        xaxis_tickformat='%d/%m',       # Formatar a data no eixo X
        width=1900,                     # Definindo a largura do gráfico
        height=700,                     # Definindo a altura do gráfico
        plot_bgcolor='white'            # Muda a cor do background
    )
    
    fig.update_traces(
        marker_size=12
    )
    
    fig.update_xaxes(
        mirror=True,
        ticks='outside',
        showline=True,
        linecolor='lightgrey',
        gridcolor='lightgrey'
    )
    fig.update_yaxes(
        mirror=True,
        ticks='outside',
        showline=True,
        linecolor='lightgrey',
        gridcolor='lightgrey'
    )
    
    # Converter o gráfico para HTML
    conn_line_html = pio.to_html(fig, full_html=False)
    
    formatted_actual_complete = f"{year}-{month:02d}"
    
    
    actual_date = datetime.now()
    formatted_actual_date = actual_date.strftime('%d/%m/%Y')
    
    data_html = generate_data_html(df, actual_date)
    
    return render_template('dashboard-mensal.html',
                           conn_line_html=conn_line_html,
                           formatted_actual_complete=formatted_actual_complete,
                           selected_month=selected_month,
                           media_cadastrados=media_cadastrados,
                           media_conectados=media_conectados,
                           media_desconectados=media_desconectados,
                           formatted_actual_date=formatted_actual_date,
                           data_html=data_html)
    
@app.route('/update_month', methods=['POST'])
def update_month():
    selected_month = request.form.get('month')
    
    # Redirecionar para o dashboard mensal com o mês selecionado
    return redirect(url_for('dashboard_mensal', month=selected_month))
    
    
    


if __name__ == '__main__':
    app.run(debug=True)
