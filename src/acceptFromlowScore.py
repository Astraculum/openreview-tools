import openreview
from tqdm import tqdm
import statistics

def find_rebuttal_examples():
    # 1. 初始化客户端 (连接到 API V2)
    client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
    
    print("正在连接 ICLR 2024 数据仓库...")
    
    # 2. 获取所有接收(Accept)的论文
    # ICLR 2024 的 Submission 包含 decision 信息，我们需要筛选 venueid 包含 Accept 的
    submissions = client.get_all_notes(
        invitation='ICLR.cc/2024/Conference/-/Submission',
        details='directReplies' # 获取回复以计算分数
    )
    
    accepted_papers = []
    print(f"共获取 {len(submissions)} 篇投稿，正在筛选接收论文...")
    
    for note in submissions:
        # 检查 venue 是否为接收状态 (Accept (Poster/Oral/Spotlight))
        venue = note.content.get('venue', {}).get('value', '')
        venue_id = note.content.get('venueid', {}).get('value', '')
        
        if 'Accept' in venue or 'Accept' in venue_id:
            accepted_papers.append(note)

    print(f"共找到 {len(accepted_papers)} 篇接收论文。正在筛选【扩散语言模型】领域的争议文章...")
    print("-" * 60)

    results = []
    
    # 3. 遍历接收论文，进行关键词和分数筛选
    for note in tqdm(accepted_papers):
        try:
            # A. 关键词筛选 (领域：扩散语言模型/文本扩散)
            title = note.content.get('title', {}).get('value', '').lower()
            abstract = note.content.get('abstract', {}).get('value', '').lower()
            text_data = title + " " + abstract
            
            # 必须包含 diffusion
            if 'diffusion' not in text_data:
                continue
            # 必须包含 语言/文本 相关词
            if not any(kw in text_data for kw in ['language', 'text', 'transformer', 'llm', 'token']):
                continue

            # B. 获取分数
            # 在 API V2 中，review 通常作为 directReplies 存在，或者需要单独 fetch
            # 这里我们再次确认 review
            forum_id = note.id
            reviews = client.get_notes(
                forum=forum_id, 
                invitation='ICLR.cc/2024/Conference/-/Official_Review'
            )
            
            if not reviews:
                continue
                
            scores = []
            for review in reviews:
                # ICLR 2024 评分格式通常为 "8: Strong Accept"，提取冒号前的数字
                rating_str = review.content.get('rating', {}).get('value', '')
                if rating_str:
                    score = int(rating_str.split(':')[0])
                    scores.append(score)
            
            if not scores:
                continue
                
            avg_score = statistics.mean(scores)
            min_score = min(scores)
            
            # C. 核心筛选标准：寻找“逆风翻盘”的样本
            # 条件1: 均分低于 6 (处于边缘，靠 Rebuttal 救回)
            # 条件2: 虽然均分还可以，但有一个非常低的分数 (<=4)，说明作者成功反驳了该审稿人
            is_controversial = avg_score < 6.0 or min_score <= 4
            
            if is_controversial:
                results.append({
                    'title': note.content.get('title', {}).get('value', ''),
                    'url': f"https://openreview.net/forum?id={forum_id}",
                    'avg_score': round(avg_score, 2),
                    'scores': sorted(scores),
                    'keywords': 'Diffusion + NLP'
                })
                
        except Exception as e:
            continue

    # 4. 输出结果，按分数从低到高排序 (分数越低越难Rebuttal，学习价值越高)
    results.sort(key=lambda x: x['avg_score'])
    
    print("\n" + "="*60)
    print(f"筛选完成！为您找到 {len(results)} 篇极具学习价值的 Rebuttal 范例：")
    print("="*60 + "\n")
    
    for idx, p in enumerate(results):
        print(f"{idx+1}. [均分 {p['avg_score']}] 分布: {p['scores']}")
        print(f"   标题: {p['title']}")
        print(f"   链接: {p['url']}")
        print("   建议关注点: 查看作者如何回复那个打低分的审稿人")
        print("-" * 30)

if __name__ == "__main__":
    find_rebuttal_examples()