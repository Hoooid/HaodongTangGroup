---
# Leave the homepage title empty to use the site title
title:
date: 2022-10-24
type: landing

sections:
  - block: hero
    content:
      title: |
        Nano Photonics
        Research Group
      image:
        filename: Probstation.jpg
      text: |
        <br>
        
        The **Nano Photonics Research Group** at Shenzhen Technology University works across colloidal quantum dots, perovskite optoelectronics, short-wave infrared photodetectors, imaging arrays, and chip-compatible integration, connecting materials synthesis, device physics, and system-level validation.
        
  - block: markdown
    content:
      title:
      subtitle:
      text: |
        <section class="np-home-recruit">
          <div class="np-home-recruit-copy">
            <p class="np-home-kicker">Prospective Students</p>
            <h2>Join a materials-to-chip optoelectronics lab.</h2>
            <p>We welcome students who want to work across colloidal quantum-dot materials, thin-film optoelectronic devices, short-wave infrared photodetectors, imaging systems, and CMOS-compatible integration.</p>
            <div class="np-home-recruit-actions">
              <a class="btn btn-primary" href="./join/">Join Us</a>
              <a class="btn btn-outline-primary" href="./publication/">See publications</a>
            </div>
          </div>
          <div class="np-home-stats" aria-label="Group highlights">
            <div><strong>90+</strong><span>Papers and Conference Records</span></div>
            <div><strong>5</strong><span>Research Directions</span></div>
            <div><strong>16</strong><span>Team and Collaborator Profiles</span></div>
            <div><strong>1</strong><span>Materials-to-Chip Research Path</span></div>
          </div>
        </section>
    design:
      columns: '1'
      spacing:
        padding: ['0', '0', '0', '0']
      css_class: np-home-recruit-section
        
  
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
        {{% cta cta_link="./people/" cta_text="Meet the team →" %}}
    design:
      columns: '1'
---
