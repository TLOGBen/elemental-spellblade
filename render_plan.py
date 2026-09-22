import json
from pathlib import Path
from tes import WORK, ROOT

def main():
    plan=json.loads((WORK/'plan.json').read_text(encoding='utf-8'))
    assert len(plan['branches'])==13
    assert len({b['id'] for b in plan['branches']})==13
    assert all(len(b['skills'])==5 for b in plan['branches'])
    assert sum(len(b['skills']) for b in plan['branches'])==65
    # Keep newly authored player-facing content in Traditional Chinese.
    replacements={'冻结':'凍結','终階':'終階','终':'終','独立':'獨立','独':'獨','無限':'無限','无限':'無限','减抗':'減抗','满層':'滿層','达':'達','触發':'觸發'}
    raw=json.dumps(plan,ensure_ascii=False,indent=2)
    for old,new in replacements.items(): raw=raw.replace(old,new)
    (WORK/'plan.json').write_text(raw+'\n',encoding='utf-8')
    plan=json.loads(raw)
    html=(WORK/'plan-template.html').read_text(encoding='utf-8').replace('__PLAN_JSON__',raw.replace('</','<\\/'))
    folder=ROOT/'.codex/show-me';folder.mkdir(exist_ok=True)
    output=folder/'元素魔戰士規劃.html';output.write_text(html,encoding='utf-8')
    md=['# 元素魔戰士規劃草案','',plan['status'],'','13 個分支，各五階，共 65 個節點。','',plan['neutralAssumption'],'']
    for branch in plan['branches']:
        md+=['## '+branch['name'],'',branch['role'],'','生效：'+branch['active'],'',branch['base'],'','| 階級 | 技能 | 效果 | 觸發與限制 |','|---|---|---|---|']
        for tier,skill in zip(plan['tiers'],branch['skills']):md.append(f"| {tier['name']}（{tier['level']}） | {skill['name']} | {skill['effect']} | {skill['trigger']}；{skill['limit']} |")
        md+=['','特效：'+branch['visual'],'']
    for heading,key in [('傷害規則','rules'),('成長','progression'),('框架','framework')]:
        md+=['## '+heading,'']
        for row in plan[key]:md+=['- **'+row['title']+'**：'+row['text']]
        md+=['']
    (WORK/'元素魔戰士規劃.md').write_text('\n'.join(md),encoding='utf-8')
    print(output)

if __name__=='__main__':main()
