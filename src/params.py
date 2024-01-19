draftkings: bool = True
singlegame: bool = True

site: str = {
    True: 'draftkings',
    False: 'fanduel'
}[draftkings]


mode: str = {
    True: 'single-game',
    False: 'main-slate'
}[singlegame]