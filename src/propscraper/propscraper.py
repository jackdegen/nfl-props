import os
import requests
import datetime

import numpy as np
import pandas as pd

from bs4 import BeautifulSoup

from typing import Callable

import customsettings

# Returns current date as string in desired format for files
def date_path() -> str:
    return '.'.join([
        datetime.datetime.now().strftime("%m%d%y"),
        # (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%m%d%y"),
        'csv'
    ])

class Conversions:
    
    def __init__(self):
        
        self.inits_issues: dict[str,str] = {
            'JAC': 'JAX'
        }
        
        self.inits_teams: dict[str, str] = {
            'ARI': 'Arizona Cardinals',
            'ATL': 'Atlanta Falcons',
            'BAL': 'Baltimore Ravens',
            'BUF': 'Buffalo Bills',
            'CAR': 'Carolina Panthers',
            'CHI': 'Chicago Bears',
            'CIN': 'Cincinnati Bengals',
            'CLE': 'Cleveland Browns',
            'DAL': 'Dallas Cowboys',
            'DEN': 'Denver Broncos',
            'DET': 'Detroit Lions',
            'GB':  'Green Bay Packers',
            'HOU': 'Houston Texans',
            'IND': 'Indianapolis Colts',
            'JAX': 'Jacksonville Jaguars', # **
            'KC':  'Kansas City Chiefs',
            'LAC': 'Los Angeles Chargers',
            'LAR': 'Los Angeles Rams',
            'LV' : 'Las Vegas Raiders',
            'MIA': 'Miami Dolphins',
            'MIN': 'Minnesota Vikings',
            'NE':  'New England Patriots',
            'NO':  'New Orleans Saints',
            'NYG': 'New York Giants',
            'NYJ': 'New York Jets',
            'PHI': 'Philadelphia Eagles',
            'PIT': 'Pittsburgh Steelers',
            'SEA': 'Seattle Seahawks',
            'SF':  'San Francisco 49ers',
            'TB':  'Tampa Bay Buccaneers',
            'TEN': 'Tennessee Titans',
            'WAS': 'Washington Commanders',
        }

        # Invert
        self.teams_inits: dict[str,str] = { val: key for key, val in self.inits_teams.items() }
        
#         scoresandodds.com: FanDuel name
        self.name_issues: dict[str,str] = {
            'Gabriel Davis': 'Gabe Davis',
            'Mitchell Trubisky': 'Mitch Trubisky'

        }
    
        
    def team_name(self, team_str: str) -> str:
        return self.teams_inits[team_str]
    
    def team_initials(self, team_init_str: str) -> str:
        return self.inits_teams[team_init_str]
    
    def player_name(self, name: str):
        return self.name_issues.get(name,name)
    
    def initals_issue(self, team_inits: str) -> str:
        return self.inits_issues.get(team_inits,team_inits)
    
    
    

class PropScraper:
    
    def __init__(self):
        """
        Class to scrape individual player props and convert to FPTS
        """
        self.convert = Conversions()
        self.directory_url: str = 'https://www.scoresandodds.com/nfl/players'
        
        self.current_date_str = datetime.datetime.now().strftime("%m/%d")
        # self.current_date_str = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%m/%d")
        # self.prop_frames = list()
        
    
#     Creates a dictionary containing the links to current and historical props
#     for every player in the NFL, organized by team
    def create_webpage_directory(self) -> dict[str, dict[str, str]]:
        
#         Load HTML into bs4
        soup = BeautifulSoup(
            requests.get(self.directory_url).text,
            'html.parser'
        )

#         Load each team data into dictionary, converting the full team name into initials as used in rest of data
        team_modules = {
            self.convert.team_name(team_html.find('h3').get_text()): team_html.find_all('div', class_='module-body')[0].find('ul')
            for team_html in soup.find_all('div', class_='module')
        }
        
        
        clean_name: Callable[[str],str] = lambda name: self.convert.player_name(' '.join(name.split(' ')[:2]).replace('.', ''))
        
#         Parse HTML data for each team to organize links in easily searchable manner
        teams_players_links: dict[str, dict[str, str]] = {
            
            team: {
                clean_name(a_tag.get_text()): self.directory_url.replace(
                    '/nfl/players',
                    a_tag['href']
                )
                for a_tag in module.find_all('a')
            }
            
            for team, module in team_modules.items()
            
        }
        
        return teams_players_links
    
    # Implied Probability = 100 / (Odds + 100)
    @staticmethod
    def pos_ml_prob(ml: str) -> float:
        return 100 / sum([int(ml[1:]),100])
    
    # Implied Probability = (-1*(Odds)) / (-1(Odds) + 100) ->
    @staticmethod
    def neg_ml_prob(ml: str) -> float:
        ml: int = int(ml)
        return (-1*ml) / sum([-1*ml,100])
        
    @classmethod
    def implied_probability(cls, ml: str):
        if ml == '+100':
            return 0.5
        
        return cls.pos_ml_prob(ml) if ml[0]=='+' else cls.neg_ml_prob(ml)
    
    @classmethod
    def expected_value(cls, val: float, ml: str) -> float:
        return cls.implied_probability(ml)*val
        
    def scrape_player_props(
        self, 
        name: str, 
        url: str, 
        site: str,
        **kwargs
    ) -> tuple[float,float]:
        
#         Load HTML
        soup = BeautifulSoup(
            requests.get(url).text, 
            'html.parser'
        )
        
        # module = soup.find('div', class_="module-body scroll")
        
        try:
            if not len(soup.find_all('span')):
                return (0.0,0.0)
        except AttributeError:
            return (0.0, 0.0)
        
#         Make sure current
        zerofill = lambda dp: f'0{dp}' if len(dp) == 1 else dp
        date_str = '/'.join([
            zerofill(dp) for dp in soup.find_all('span')[18].get_text().split(' ')[1].split('/')
        ])

        
        if date_str != self.current_date_str:
            return (0.0, 0.0)

        # props_rows = soup.find('table', class_='sticky').find('tbody').find_all('tr')
        try:
            props_rows = soup.find('table', class_='sticky').find('tbody').find_all('tr')

        except AttributeError:
            print(f'{name} -> Still failing here...')
            # return (0.0, 0.0)
        
        # Steals, blocks are options but noisy, better to use season data for opponents
        
        site_targets: dict[str,tuple[str,...]] = {
            'fanduel': (
                'Rushing Yards',
                'Receiving Yards',
                'Receptions',
                'Touchdowns',
                'Passing Tds',
                'Passing Yards',
                'Interceptions',
            ),
            'draftkings': (
                'Rushing Yards',
                'Receiving Yards',
                'Receptions',
                'Touchdowns',
                'Passing Tds',
                'Passing Yards',
                'Interceptions',
            )
        }

        # Form: Category Line Over Under
        target_rows = [row for row in props_rows if row.find('td').get_text() in site_targets[site]]
    
        # TODO: Figure out more efficient way for this, dict(zip()) probably best
        props = {
            # 'name': list(),
            'stat': list(),
            'value': list(),
            # 'over': list(),
            'e_value': list(),
            'fpts': list(),
            'e_fpts': list()
            # 'under': list()
        }
        
        
        site_multipliers: dict[str,dict[str,float]] = {
            'fanduel': {
                'Rushing Yards': 0.1,
                'Receiving Yards': 0.1,
                'Receptions': 0.5,
                'Touchdowns': 0.0 if kwargs.get('mute_touchdowns', True) else 6.0,
                'Passing Tds': 4.0,
                'Passing Yards': 0.04,
                'Interceptions': -1.0
            },
            'draftkings': {
                'Rushing Yards': 0.1,
                'Receiving Yards': 0.1,
                'Receptions': 1.0,
                'Touchdowns': 0.0 if kwargs.get('mute_touchdowns', True) else 6.0,
                'Passing Tds': 4.0,
                'Passing Yards': 0.04,
                'Interceptions': -0.5
            },
        }
        
        multipliers: dict[str,float] = {k.lower(): v for k,v in site_multipliers[site].items()}
        for rowtags in target_rows:
            vals = [val.get_text().lower() for val in rowtags.find_all('td')] # (Category, Line, Over, Under)
            
            stat: str = vals[0].strip()
            props['stat'].append(stat)

            # Convert to whole number
            # statval = sum([float(vals[1]), 0.5])
            statval = sum([float(vals[1]), 0.0])
            props['value'].append(statval)
            
            overml: str = vals[2]
            
            props['e_value'].append(self.expected_value(statval, overml))

            multi: float = multipliers.get(stat, 1.0)
            fpts: float = multi*statval
            
            props['fpts'].append(fpts)
            props['e_fpts'].append(self.expected_value(fpts, overml))
            # props['under'].append(vals[3])
        
        
        df: pd.DataFrame = pd.DataFrame(props).round(2)
        
        
        return (df['fpts'].sum(), df['e_fpts'].sum())
