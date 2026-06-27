import os

target_dir = os.path.join('result', 'Arjun Appadurai 《The Social Life of Things Commodities in Cultural Perspective》')
target_file = os.path.join(target_dir, '10-Introduction commodities and the politics of value.md')

lines = []
lines.append('# 章节知识分析：Introduction: commodities and the politics of value')
lines.append('')
lines.append('## Chapter Knowledge Analysis: Introduction: commodities and the politics of value')
lines.append('')
lines.append('---')
lines.append('')
lines.append('### 一、核心主题 / Core Theme')
lines.append('')
lines.append('Commodities generate divergent mythologies when knowledge about their trajectories of circulation is segmented across producers, traders, and consumers -- a phenomenon explored through three cross-cultural case studies (commodity futures markets, cargo cults, and Bolivian tin-mining rituals) that together reveal how the fetishism of commodities and the commoditization of knowledge operate in vastly different economic systems.')
lines.append('')
lines.append('---')
lines.append('')
lines.append('### 二、知识维度 / Knowledge Dimensions')
lines.append('')
lines.append('#### 维度一：Mythologies of Circulation and the Fragmentation of Knowledge / 流通神话与知识碎片化')
lines.append('')
lines.append('**核心议题 / Topics**:')
lines.append('- Commodity futures markets as semiotic play divorced from consumption')
lines.append('- Cargo cults as mythologies of the alienated consumer')
lines.append('- Bolivian tin-mining devil rituals as mythologies of the alienated producer')
lines.append('- Segmented knowledge across production, distribution, and consumption loci')

with open(target_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('Phase 1 written OK')
