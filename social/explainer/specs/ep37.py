from dkengine import W,CORAL,TQ,NAVY
R='/home/claude/barur-site/social/heygen/'
NUM=37; RAW=R+"raw/dk37-three-questions.mp4"; WORDS=R+"words/dk37-three-questions.json"
HL=['שאלות','לצאת','תעלה','כלול','ברורות','להבין']
END_FROM='איזו'
SCENES=[
 {'word':'שאלות','els':[('head',0,'לפני שחותמים: *3 שאלות*',74,780),('icon','לשאול','chat',W/2,970,140)]},
 {'at':'אחת','word':'לצאת','els':[('chips',[('לצאת','1. כמה עולה *לצאת מכל מסלול?*','unlock'),('תעלה','2. מה קורה *אם הריבית תעלה?*','up'),('כלול','3. מה *כלול*, ומה ~בנפרד?~','doc')],820,150)]},
 {'at':'אם','word':'ברורות','els':[('cards',[('ברורות','ברור? *מצוין*','check',True),('לעצור','לא? ~עוצרים~','warning',False,CORAL)],900)]},
 {'at':'זו','word':'להבין','els':[('head','התחייבות','התחייבות ל*20–30 שנה*',72,780),('lines',[('להבין','מגיע לכם *להבין אותה*',62)],970,0)]},
]
