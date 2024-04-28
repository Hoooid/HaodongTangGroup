---
# Leave the homepage title empty to use the site title
title:
date: 2022-10-24
type: landing

sections:
  - block: hero
    content:
      title: |
        **纳米光子与芯片集成实验室**
      image:
        filename: Probstation.jpg
      text: |
        <br>
        
        **纳米光子与芯片集成实验室**依托深圳技术大学集成电路与光电芯片学院，旨在探索在纳米尺度操控光子的前沿领域，融合光学、光电子学、半导体物理等学科，以实现各种半导体光电器件的芯片集成。
        
  
  - block: collection
    content:
      title: Latest News
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
          filename: devices.jpg
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
        {{% cta cta_link="./people/" cta_text="Meet the team →" %}}
    design:
      columns: '1'
---