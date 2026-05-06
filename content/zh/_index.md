---
# Leave the homepage title empty to use the site title
title:
date: 2022-10-24
type: landing

sections:
  - block: hero
    content:
      title: |
        纳米光子器件集成
        课题组
      image:
        filename: Probstation.jpg
      text: |
        <br>
        
        **纳米光子器件集成课题组**隶属于深圳技术大学集成电路与光电芯片学院，面向量子点、钙钛矿、二维材料、光电探测器、显示与成像芯片等方向，探索纳米尺度光调控、光电转换和芯片集成中的关键科学与工程问题。
        
  
  - block: collection
    content:
      title: 最新动态
      subtitle:
      text:
      count: 5
      filters:
        author: ''
        category: ''
        exclude_featured: false
        publication_type: ''
        tag: ''
      offset: 0
      order: desc
      page_type: post
    design:
      view: card
      columns: '1'
  
  - block: markdown
    content:
      title:
      subtitle: ''
      text:
    design:
      columns: '1'
      background:
        image: 
          filename: works.png
          filters:
            brightness: 1
          parallax: false
          position: center
          size: contain
          text_color_light: true
      spacing:
        padding: ['20px', '0', '20px', '0']
      css_class: fullscreen
  
  - block: markdown
    content:
      title:
      subtitle:
      text: |
        {{% cta cta_link="./people/" cta_text="了解团队 →" %}}
    design:
      columns: '1'
---
