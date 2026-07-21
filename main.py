import pandas as pd
import numpy as np
import plotly.graph_objs as go

def standartize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    lat_candidates  = ['lat', 'latitude', 'Lat', 'Latitude', 'LAT', 'LATITUDE']
    lon_candidates  = ['lon', 'longitude', 'Lon', 'Longitude', 'Lng']
    cost_candidates = ['custo', 'valor', 'cost', 'price', 'preco']
    name_candidates = ['nome', 'name', 'title', 'local', 'place']

    def pick(colnames, candidates):
        # captura a coluna correta usando os nomes das colunas com os possíveis candidatos
        for c in candidates:
            # percorre candidato (c) dentro da lista de candidatos
            if c in colnames:
                # se o candidato for extamente igual a um dos nomes em colnames (colunas das tabela)
                return c # retorna esse candidato imediatamente
        for c in candidates:
            # se não encontrou a correspondência exata, percorre novamente
            for col in colnames:
                # faz igual ao de cima, mas trabalhando em minúsculas apenas
                if c.lower() in col.lower():
                    return col
        return None # se não encontrou nada nem exato nem parcial, retorna None (nenhum match encontrado)
                
    lat_col = pick(df.columns, lat_candidates)
    lon_col = pick(df.columns, lon_candidates)
    cost_col = pick(df.columns, cost_candidates)
    name_col = pick(df.columns, name_candidates)

    if lat_col is None or lon_col is None: # não é possível demarcar o ponto no mapa
        # apresenta o erro sem impactar no funcionamento do programa
        raise ValueError(f"Não encontrei colunas de latitude e longitude {list(df.columns)}")
    
    out = pd.DataFrame()
    out['lat']      = pd.to_numeric(df[lat_col], errors = 'coerce') # coerce força a conversão
    out['lon']      = pd.to_numeric(df[lon_col], errors = 'coerce')
    out['custo']    = pd.to_numeric(df[cost_col], errors = 'coerce') if cost_col is not None else np.nan  # se não for vazio, converte para numérico
    # converte para string para não dar problema lá embaixo (débito técnico) e precisar converter três vezes
    # aqui já converte uma vez só
    # astype é melhor que to_string na performance
    out['nome']     = df[name_col].astype(str) if name_col is not None else [f'Ponto {i}' for i in range(len(df))]

    # remover linhas sem coordenadas
    out = out.dropna(subset=['lat', 'lon']).reset_index(drop=True)

    # preenche custos ausentes
    if out['custo'].notna().any():
        med = float(out['custo'].median())
        if not np.isfinite(med):
            med = 1.0
        out['custo'] = out['custo'].fillna(med)
    else:
        out['custo'] = 1.0
    return out # out é um dataframe

def city_center(df : pd.DataFrame) -> dict:
    return dict(
        lat = float(df['lat'].mean()),
        lon = float(df['lon'].mean())
    )

# ----------------------- Traces do gráfico ------------------------------
def make_point_trace(df:pd.DataFrame, name:str) -> go.Scattermap:
    hover = ('<b>%{customdata[0]}</b><br>Custo:%{customdata[1]}<br>Lat:%{customdata[2]}<br>Lon:%{customdata[3]}')
    c = df['custo'].astype(float).values
    c_min, c_max = float(np.min(c)), float(np.max(c))

    # Caso especial: se não existiem valores numéricos válidos ou se todos os custom forem praticamente iguais (diferença < 1e-9 (0.000000001)) criaremos um array de tamanhos fixos para todos os pontos
    # isfinite para ver se é válido
    if not np.isfinite(c_min) or not np.isfinite(c_max) or abs(c_max - c_min) < 1e-9:
        size = np.full_like(c, 10.0, dtype=float)
    else:
        # Caso normal: normaliza os custos para o intervalo (0.1) e escala para variar entre 6 e 26 (20 de amplitude mais 6 de deslocamento)
        # pontos de custo baixo ~6, pontos de custo alto ~26
        size = ((c - c_min) / (c_max - c_min) * 20) + 6
        # mesmo que os dados estejam fora da faixa de 6 e 26, ele evita apresentar essa informação, forçando a ficar entre o intervalo
    sizes = np.clip(size, 6, 26)
    custom = np.stack([df['nome'].values, df['custo'].values, df['lat'].values, df['lon'].values], axis = 1)
    # axis 1 (1 = coluna) empilha as colunas lado a lado
    return go.Scattermap(
        lat=    df['lat'],
        lon=    df['lon'],
        mode=   'markers',
        marker= dict(
            size =  sizes,
            color = df['custo'],
            colorscale = 'Viridis',
            colorbar = dict({'title': 'Custo'})
        ),
        name=   f'{name} • Pontos',
        hovertemplate=  hover,
        customdata=     custom
    )

def make_density_trace(df: pd.DataFrame, name: str) -> go.Densitymap:
    return go.Densitymap(
        lat= df['lat'],
        lon= df['lon'],
        radius= 20,
        z= df['custo'],
        colorscale= 'Inferno',
        name = f'{name} • Pontos',
        showscale= True,
        colorbar= dict(title='Custo')
    )
    
# ----------------------- Main ------------------------------
def main():
    # carrega e padroniza os dados
    pasta = 'C:/Users/N1636870/OneDrive - Liberty Mutual/Desktop/Treinamento Python/02-Avançado/airbnb'
    rj = standartize_columns(pd.read_csv(f'{pasta}/RJ.csv'))
    ny = standartize_columns(pd.read_csv(f'{pasta}/NY.csv'))
    sp = standartize_columns(pd.read_csv(f'{pasta}/SP.csv'))
    st = standartize_columns(pd.read_csv(f'{pasta}/santiago.csv'))

    # criamos os quatro traces
    ny_point = make_point_trace(ny, "New York")
    ny_heat = make_density_trace(ny, "New York")    

    rj_point = make_point_trace(rj, "Rio de Janeiro")
    rj_heat = make_density_trace(rj, "Rio de Janeiro")

    sp_point = make_point_trace(sp, "São Paulo")
    sp_heat  = make_density_trace(sp, "São Paulo")

    st_point = make_point_trace(st, "Santiago")
    st_heat  = make_density_trace(st, "Santiago")

    fig = go.Figure([ny_point, ny_heat, rj_point, rj_heat, sp_point, sp_heat, st_point, st_heat])

    # função para aproximar o mapa (executado dentro do gráfico mais tarde)
    def center_zoom(df, zoom):
        return dict(center=city_center(df), zoom=zoom)
    
    # dropdown simples com quatro opções (cidade x visualização)
    buttons=[
        dict(
            label = 'New York • Pontos',
            method = 'restyle',
            args = [
                {'visible': [True, False, False, False, False, False, False, False]}, # apenas este visível
                {'map': center_zoom(ny, 9)}
            ]
        ),
        dict(
            label = 'New York • Calor',
            method = 'restyle',
            args = [
                {'visible': [False, True, False, False, False, False, False, False]}, # apenas este visível (o segundo)
                {'map': center_zoom(ny, 9)}
            ]
        ),
        dict(
            label = 'Rio de Janeiro • Pontos',
            method = 'restyle',
            args = [
                {'visible': [False, False, True, False, False, False, False, False]}, # apenas este visível (o terceiro)
                {'map': center_zoom(rj, 2)}
            ]
        ),
        dict(
            label = 'Rio de Janeiro • Calor',
            method = 'restyle',
            args = [
                {'visible': [False, False, False, True, False, False, False, False]}, # apenas este visível
                {'map': center_zoom(rj, 2)}
            ]
        ),
        dict(
            label = 'São Paulo • Pontos',
            method = 'restyle',
            args = [
                {'visible': [False, False, False, False, True, False, False, False]}, # apenas este visível (o terceiro)
                {'map': center_zoom(rj, 10)}
            ]
        ),
        dict(
            label = 'São Paulo • Calor',
            method = 'restyle',
            args = [
                {'visible': [False, False, False, False, False, True, False, False]}, # apenas este visível
                {'map': center_zoom(sp, 10)}
            ]
        ),
        dict(
            label = 'Santiago • Pontos',
            method = 'restyle',
            args = [
                {'visible': [False, False, False, False, False, False, True, False]}, # apenas este visível (o terceiro)
                {'map': center_zoom(st, 5)}
            ]
        ),
        dict(
            label = 'Santiago • Calor',
            method = 'restyle',
            args = [
                {'visible': [False, False, False, False, False, False, False, True]}, # apenas este visível
                {'map': center_zoom(st, 5)}
            ]
        )
    ]

    fig.update_layout(
        title = 'Mapa Interativo de Custos - Pontos e Calor',
        mapbox_style = 'open-street-map',
        mapbox = dict(center = city_center(rj), zoom=10),
        margin = dict(l=10, r=10, t=50, b=10),
        updatemenus = [dict(
            buttons = buttons,
            direction = 'down',
            xanchor = 'left',
            yanchor = 'top',
            x = 0.01, 
            y = 0.99,
            bgcolor = 'white',
            bordercolor = 'lightgray'
        )],
        legend = dict(
            orientation = 'h',
            yanchor = 'bottom',
            xanchor = 'right',
            y = 0.01,
            x = 0.99
        )
    )

    # salva em HTML de apresentação (standalone)
    fig.write_html(
        f'{pasta}/mapa_custos_interativos.html',
        include_plotlyjs = 'cdn',
        full_html = True
    )
    print(f'Arquivo gerado com sucesso em {pasta}/mapa_custos_interativos.html.')

# Iniciar o servidor
if __name__ == '__main__':
    main()