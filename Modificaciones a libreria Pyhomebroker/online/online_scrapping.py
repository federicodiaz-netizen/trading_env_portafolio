#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Home Broker API - Market data downloader
# https://github.com/crapher/pyhomebroker.git
#
# Copyright 2020 Diego Degese
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from ..common import user_agent, DataException, SessionException, ServerException
from .online_core import OnlineCore

import requests as rq
import pandas as pd
import numpy as np

class OnlineScrapping(OnlineCore):

    def __init__(self, auth, proxy_url=None):
        """
        Class constructor.

        Parameters
        ----------
        auth : home_broker_session
            An object with the authentication information.
        proxy_url : str, optional
            The proxy URL with one of the following formats:
                - scheme://user:pass@hostname:port
                - scheme://user:pass@ip:port
                - scheme://hostname:port
                - schemeC

            Ex. https://john:doe@10.10.1.10:3128
        """

        self._proxies = {'http': proxy_url, 'https': proxy_url} if proxy_url else None
        self._auth = auth
        self.personal_portfolio_gerencial = None

########################
#### PUBLIC METHODS ####
########################
    def get_personal_portfolio(self):
        import pandas as pd
        import numpy as np

        # 1. OBTENCIÓN Y APLANADO
        raw_data = self.__get_personal_portfolio()
        portfolio_list = []

        if raw_data and isinstance(raw_data, dict):
            if 'Result' in raw_data and isinstance(raw_data['Result'], dict):
                if 'Activos' in raw_data['Result']:
                    grupos = raw_data['Result']['Activos']
                    for grupo in grupos:
                        categoria = grupo.get('ESPE', '')
                        if isinstance(grupo, dict) and 'Subtotal' in grupo:
                            items = grupo['Subtotal']
                            if isinstance(items, list):
                                for item in items:
                                    item['_Category'] = categoria 
                                portfolio_list.extend(items)

        if not portfolio_list:
             # Inicializamos vacío para evitar errores si se consulta antes de tiempo
             self.personal_portfolio_gerencial = pd.DataFrame()
             return [pd.DataFrame(), pd.DataFrame()]
             
        df = pd.DataFrame(portfolio_list)

        # 2. RENOMBRADO
        rename_map = {
            'TICK': 'Symbol', 'ESPE': 'Description', 'CANT': 'Quantity',
            'IMPO': 'Amount', 'PCIO': 'LastPrice', 'CAN0': 'PPC',
            'CAN2': 'Weight', 'CAN3': 'ChangePct', 'TIPO': 'Settlement'
        }
        df.rename(columns=rename_map, inplace=True)

        # 3. LIMPIEZA Y CÁLCULOS
        if 'Symbol' in df.columns and 'Description' in df.columns:
            df['Symbol'] = df.apply(lambda x: x['Description'] if pd.isna(x['Symbol']) or str(x['Symbol']).strip() == '' else x['Symbol'], axis=1)

        numeric_cols = ['Quantity', 'Amount', 'LastPrice', 'PPC']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(np.float64)

        float_cols = ['Weight', 'ChangePct']
        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round(2)

        if 'Amount' in df.columns and 'PPC' in df.columns and 'Quantity' in df.columns:
            # --- CORRECCIÓN DE MULTIPLICADOR PARA OPCIONES ---
            # Detectamos si es opción de Galicia (Call=GFGC, Put=GFGV) u otras que empiecen igual.
            # Si tuvieras opciones de otras acciones, agrega sus prefijos en startswith.
            es_opcion = df['Symbol'].astype(str).str.startswith(('GFGC', 'GFGV'), na=False)
            
            # Si es opción, multiplicador = 100. Si no, = 1.
            multiplicador = np.where(es_opcion, 100, 1)
            
            # Cálculo: ValorActual - (CostoUnitario * Cantidad * Multiplicador)
            df['PnL'] = df['Amount'] - (df['PPC'] * df['Quantity'] * multiplicador)
        else:
            df['PnL'] = 0.0

        def arreglar_plazo(valor):
            s = str(valor).lower().strip()
            if 'spot' in s or 'ci' in s or 'inmediato' in s: return 'spot'
            if '48' in s: return '48hs'
            return '24hs' 

        if 'Settlement' in df.columns:
            df['Settlement'] = df['Settlement'].apply(arreglar_plazo)
        else:
            df['Settlement'] = '24hs'

        # 4. GUARDADO EN MEMORIA (Para xlwings)
        # Seleccionamos las columnas útiles para tu reporte gerencial
        cols_reporte = ['Symbol', 'Description', 'Quantity', 'LastPrice', 'PPC', 'Amount', 'PnL', 'ChangePct', 'Weight', 'Settlement']
        
        for col in cols_reporte:
            if col not in df.columns: df[col] = 0.0 if col not in ['Symbol','Description','Settlement'] else ''
            
        # --- VARIABLE DE ACCESO PÚBLICO ---
        # Aquí es donde xlwings buscará los datos completos (Dinero + Acciones)
        self.personal_portfolio_gerencial = df[cols_reporte].copy()

        # 5. PREPARACIÓN LIBRERÍA (FILTRADO TÉCNICO)
        # Filtramos el dinero para que el robot de precios no falle
        mask_dinero = df['Symbol'].astype(str).str.contains('Pesos|USD|Dolar|Extranjera', case=False, na=False)
        df_lib = df[~mask_dinero].copy()

        # Eliminamos basura técnica innecesaria
        df_lib.drop(columns=['APERTURA', 'TESP', 'NERE', 'GTOS', 'DETA', 'AMPL', 'DIVI', 'Moneda', 'Hora'], inplace=True, errors='ignore')

        df_lib['symbol'] = df_lib['Symbol'].astype(str)
        
        # Corrección de plazo para Opciones vs Acciones
        if '_Category' in df_lib.columns:
            def corregir_lib(row):
                if 'opciones' in str(row['_Category']).lower(): return ''
                return row['Settlement']
            df_lib['settlement'] = df_lib.apply(corregir_lib, axis=1)
        else:
            df_lib['settlement'] = df_lib['Settlement']

        # Rellenos obligatorios para la librería
        df_lib['close'] = df_lib['LastPrice']
        df_lib['last'] = df_lib['LastPrice']
        for col in ['open', 'high', 'low', 'bid', 'ask', 'volume', 'turnover']:
            df_lib[col] = 0.0

        return [df_lib, pd.DataFrame()]

    def get_securities(self, board, settlement):
        """
        Returns the security board specified by the name and settlement.

        Parameters
        ----------
        board : str
            The name of the board to be retrieved.
            Valid values: accionesLideres, panelGeneral, cedears, rentaFija, letes, obligaciones.
        settlement : int
            The settlement of the board to be retrieved.
            Valid values: 1, 2, 3.

        Raises
        ------
        pyhomebroker.exceptions.SessionException
            If the user is not logged in.
        pyhomebroker.exceptions.ServerException
            When the server returns an error in the response.
        pyhomebroker.exceptions.DataException
            When the board name or the settlement is not valid.
        requests.exceptions.HTTPError
            There is a problem related to the HTTP request.

        Returns
        -------
        An empty dataframe or a dataframe with the quotes.
        """

        data = self.__get_predefined_portfolio(board, settlement)
        df = pd.DataFrame(data['Result']['Stocks']) if data['Result'] and data['Result']['Stocks'] else pd.DataFrame()

        return self.process_securities(df)

    def get_options(self):
        """
        Returns the options board.

        Raises
        ------
        pyhomebroker.exceptions.SessionException
            If the user is not logged in.
        pyhomebroker.exceptions.ServerException
            When the server returns an error in the response.
        requests.exceptions.HTTPError
            There is a problem related to the HTTP request.

        Returns
        -------
        An empty dataframe or a dataframe with the quotes.
        """

        data = self.__get_predefined_portfolio('opciones')
        df = pd.DataFrame(data['Result']['Stocks']) if data['Result'] and data['Result']['Stocks'] else pd.DataFrame()

        return self.process_options(df)

    def get_repos(self):
        """
        Returns the repo board.

        Raises
        ------
        pyhomebroker.exceptions.SessionException
            If the user is not logged in.
        pyhomebroker.exceptions.ServerException
            When the server returns an error in the response.
        requests.exceptions.HTTPError
            There is a problem related to the HTTP request.

        Returns
        -------
        An empty dataframe or a dataframe with the repos.
        """

        data = self.__get_predefined_portfolio('cauciones')
        df = pd.DataFrame(data['Result']['Stocks']) if data['Result'] and data['Result']['Stocks'] else pd.DataFrame()

        return self.process_repos(df)

    def get_order_book(self, symbol, settlement=None):
        """
        Returns the order book specified by the name and settlement.

        Parameters
        ----------
        symbol : str
            The asset symbol or the repo currency.
        settlement : str
            The settlement of the board to be retrieved.
            Valid values:
                options: None or empty string.
                repos: datetime in format %Y%m%d (YYYYMMDD).
                rest of securities: 1, 2, 3.

        Raises
        ------
        pyhomebroker.exceptions.DataException
            When the settlement is not valid.
        pyhomebroker.exceptions.SessionException
            If the user is not logged in.
        pyhomebroker.exceptions.ServerException
            When the server returns an error in the response.
        requests.exceptions.HTTPError
            There is a problem related to the HTTP request.

        Returns
        -------
        A dataframe with quotes.
        """

        data = self.__get_asset(symbol, settlement)

        if data['Result'] and data['Result']['Stock'] and data['Result']['Stock']['StockDepthBox'] and data['Result']['Stock']['StockDepthBox']['PriceDepthBox']:
            df_buy = pd.DataFrame(data['Result']['Stock']['StockDepthBox']['PriceDepthBox']['BuySide'])
            df_sell = pd.DataFrame(data['Result']['Stock']['StockDepthBox']['PriceDepthBox']['SellSide'])
        else:
            df_buy = pd.DataFrame()
            df_sell = pd.DataFrame()

        return self.process_order_book(symbol, settlement, df_buy, df_sell)

#########################
#### PRIVATE METHODS ####
#########################
    def __get_personal_portfolio(self):
        # La URL definitiva que confirmamos
        url = 'https://cuentas.vetacapital.com.ar/Consultas/GetConsulta'
        
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/json; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://cuentas.vetacapital.com.ar/Consultas/PortafolioOnline',
            'Origin': 'https://cuentas.vetacapital.com.ar',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # El Payload exacto que capturaste del navegador
        payload = {
            "comitente": "49307",
            "comitenteMana": None,
            "consolida": "0",
            "especie": None,
            "fechaDesde": None,
            "fechaHasta": None,
            "proceso": "22"
        } 
        
        # Realizamos la petición enviando el diccionario como JSON
        response = rq.post(url, 
                           json=payload, 
                           headers=headers, 
                           cookies=self._auth.cookies,
                           proxies=self._proxies)
        
        # Si esto funciona, el status será 200
        response.raise_for_status()
        return response.json()

    def __get_predefined_portfolio(self, board, settlement=None):

        if not self._auth.is_user_logged_in:
            raise SessionException('User is not logged in')

        headers = {
            'User-Agent': user_agent,
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/json; charset=UTF-8'
        }

        url = '{}/Prices/GetByPanel'.format(self._auth.broker['page'])

        payload = {
            'panel': board,
            'term': settlement or ''
        }

        response = rq.post(url, json=payload, headers=headers, cookies=self._auth.cookies, proxies=self._proxies)
        response.raise_for_status()

        response = response.json()

        if not response['Success']:
            raise ServerException(response['Error']['Descripcion'] or 'Unknown Error')

        return response

    def __get_asset(self, symbol, settlement):

        if not self._auth.is_user_logged_in:
            raise SessionException('User is not logged in')

        headers = {
            'User-Agent': user_agent,
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/json; charset=UTF-8'
        }

        url = '{}/Prices/GetConsulta'.format(self._auth.broker['page'])

        payload = {
            'symbol': symbol,
            'term': settlement
        }

        response = rq.post(url, json=payload, headers=headers, cookies=self._auth.cookies, proxies=self._proxies)
        response.raise_for_status()

        response = response.json()

        if not response['Success']:
            raise ServerException(response['Error']['Descripcion'] or 'Unknown Error')

        return response
