(() => {
  "use strict";

  const TRANSLATIONS = {
    "skip-link": {
      en: "Skip to content",
      zh: "跳至正文",
    },
    "thesis-1": {
      en: "I am a PhD student at NJU &amp; CASIA.",
      zh: "我是南京大学与中国科学院自动化研究所联合培养的博士研究生。",
    },
    "thesis-2": {
      en: "I study embodied agents.",
      zh: "我研究具身智能体。",
    },
    "thesis-3": {
      en: "My long-term goal is to build a simple and general-purpose agent for home robots.",
      zh: "我的长期目标是为家庭机器人构建简单且通用的智能体。",
    },
    "bio-1": {
      en: `Hi! I am a second-year Ph.D. student in Computer Science and Engineering at <a href="https://www.nju.edu.cn/en/">Nanjing University</a> and the <a href="https://english.ia.cas.cn/">Institute of Automation, Chinese Academy of Sciences</a>, jointly supervised by <a href="https://cs.nju.edu.cn/huojing/">Jing Huo</a> and <a href="https://people.ucas.ac.cn/~yifanzhang">Yifan Zhang</a>. I received my M.Eng. degree in Control Science and Engineering from Nanjing University, where I was advised by <a href="https://heyuanmingong.github.io/">Zhi Wang</a> and <a href="https://ra.nju.edu.cn/szll/zzjs/20251120/i352846.html">Chunlin Chen</a>. I am also closely working with <a href="https://jayceeshi.github.io/">Jieqi Shi</a> and <a href="https://chenzixuan99.github.io/homepage/">Zixuan Chen</a>.`,
      zh: `Hi！我是<a href="https://www.nju.edu.cn/en/">南京大学</a>与<a href="https://english.ia.cas.cn/">中国科学院自动化研究所</a>联合培养的计算机科学与技术专业二年级博士研究生，由<a href="https://cs.nju.edu.cn/huojing/">霍静</a>和<a href="https://people.ucas.ac.cn/~yifanzhang">张一帆</a>共同指导。我在南京大学获得控制科学与工程专业硕士学位，导师为<a href="https://heyuanmingong.github.io/">王志</a>和<a href="https://ra.nju.edu.cn/szll/zzjs/20251120/i352846.html">陈春林</a>。我还与 <a href="https://jayceeshi.github.io/">史桀绮</a>、<a href="https://chenzixuan99.github.io/homepage/">陈子璇</a> 密切合作。`,
    },
    "bio-2": {
      en: `My current research focuses on embodied navigation and mobile manipulation. I am open to academic discussions and collaborations. Feel free to email me at <a href="mailto:skyhyding@gmail.com">skyhyding@gmail.com</a>.`,
      zh: `我目前的研究聚焦于具身导航和移动操作。欢迎学术交流与合作，您可以通过 <a href="mailto:skyhyding@gmail.com">skyhyding@gmail.com</a> 联系我。`,
    },
    "contact-email": {
      en: "Email",
      zh: "邮箱",
    },
    "contact-scholar": {
      en: "Google Scholar",
      zh: "谷歌学术",
    },
    "heading-activities": {
      en: "Recent Activities",
      zh: "近期动态",
    },
    "date-news-1": {
      en: "Jun 1, 2026",
      zh: "2026年6月1日",
    },
    "date-news-2": {
      en: "May 26, 2026",
      zh: "2026年5月26日",
    },
    "date-news-3": {
      en: "Jan 31, 2026",
      zh: "2026年1月31日",
    },
    "date-news-4": {
      en: "Oct 22, 2025",
      zh: "2025年10月22日",
    },
    "news-1": {
      en: `<strong><a href="https://jia-handsome.github.io/v-Dreamer/">V-Dreamer</a></strong> received the <strong>Best Paper Award</strong> at the <a href="https://awesomedigitaltwin.github.io/2026_ICRA.html">ICRA 2026 Workshop on Generative Digital Twins for Real2Sim and Sim2Real Transfer</a>! Congrats to Songjia!`,
      zh: `<strong><a href="https://jia-handsome.github.io/v-Dreamer/">V-Dreamer</a></strong> 获得 <a href="https://awesomedigitaltwin.github.io/2026_ICRA.html">ICRA 2026 Workshop on Generative Digital Twins for Real2Sim and Sim2Real Transfer</a> <strong>最佳论文奖</strong>！祝贺 Songjia！`,
    },
    "news-2": {
      en: `Our latest work on unified embodied navigation, <strong><a href="https://xetroubadour.github.io/Uni-LaViRA/">Uni-LaViRA</a></strong>, was released and open-sourced.`,
      zh: `我们关于统一具身导航的最新工作 <strong><a href="https://xetroubadour.github.io/Uni-LaViRA/">Uni-LaViRA</a></strong> 已发布并开源。`,
    },
    "news-3": {
      en: `<strong><a href="https://robo-lavira.github.io/lavira-zs-vln/">LaViRA</a></strong> was accepted to <strong>ICRA 2026</strong>! Congrats to Team LaViRA!`,
      zh: `<strong><a href="https://robo-lavira.github.io/lavira-zs-vln/">LaViRA</a></strong> 已被 <strong>ICRA 2026</strong> 接收！祝贺 LaViRA 团队！`,
    },
    "news-4": {
      en: `Our zero-shot vision-language navigation work, <strong><a href="https://robo-lavira.github.io/lavira-zs-vln/">LaViRA</a></strong>, was released and open-sourced.`,
      zh: `我们的零样本视觉语言导航工作 <strong><a href="https://robo-lavira.github.io/lavira-zs-vln/">LaViRA</a></strong> 已发布并开源。`,
    },
    "heading-publications": {
      en: "Selected Publications",
      zh: "代表性论文",
    },
    "status-uni-lavira": {
      en: "arXiv · 2026",
      zh: "arXiv · 2026",
    },
    "status-v-dreamer": {
      en: "<strong>🏆 ICRA 2026 Workshop Best Paper Award</strong>",
      zh: "<strong>🏆 ICRA 2026 Workshop 最佳论文奖</strong>",
    },
    "status-lavira": {
      en: "ICRA · 2026",
      zh: "ICRA · 2026",
    },
    "status-acorm": {
      en: "ICLR · 2024",
      zh: "ICLR · 2024",
    },
    "status-mfrs": {
      en: "IEEE/CAA JAS · 2023 (CAS Zone 1, Top Journal, IF: 18.3)",
      zh: "IEEE/CAA JAS · 2023（中科院一区 TOP，影响因子：18.3）",
    },
    "summary-uni-lavira": {
      en: "A unified training-free embodied navigation framework spanning VLN-CE, ObjectNav, EQA, and Aerial-VLN across multiple robot platforms.",
      zh: "一个统一的免训练具身导航框架，覆盖多种机器人平台和多种具身导航任务，例如 VLN-CE、ObjectNav、EQA 和 Aerial-VLN。",
    },
    "summary-v-dreamer": {
      en: "A fully automated framework that turns language instructions into simulation-ready scenes and executable robot trajectories using video generation priors.",
      zh: "一个利用视频生成先验，将语言指令自动转化为可用仿真场景和可执行机器人轨迹的框架。",
    },
    "summary-lavira": {
      en: "A zero-shot VLN framework that decomposes navigation into language, vision, and robot actions for stronger generalization in continuous environments.",
      zh: "一个将导航分解为语言、视觉和机器人动作的零样本 VLN 框架，增强连续环境中的泛化能力。",
    },
    "summary-acorm": {
      en: "Attention-guided contrastive role representations for heterogeneous behavior and coordination in multi-agent reinforcement learning.",
      zh: "面向多智能体强化学习异质行为与协作的注意力引导对比式角色表征方法。",
    },
    "summary-mfrs": {
      en: "A magnetic-field-based reward shaping method for efficient exploration and goal-reaching in goal-conditioned reinforcement learning.",
      zh: "一种面向目标条件强化学习的磁场奖励塑形方法，用于提升探索与目标到达效率。",
    },
    "resource-project": {
      en: "Project",
      zh: "项目",
    },
    "resource-paper": {
      en: "Paper",
      zh: "论文",
    },
    "resource-code": {
      en: "Code",
      zh: "代码",
    },
    "heading-education": {
      en: "Education",
      zh: "教育经历",
    },
    "date-edu-phd-start": {
      en: "Sep. 2024",
      zh: "2024年9月",
    },
    "date-edu-phd-end": {
      en: "Jun. 2028",
      zh: "2028年6月",
    },
    "date-expected": {
      en: "(expected)",
      zh: "（预计）",
    },
    "date-edu-master-start": {
      en: "Sep. 2021",
      zh: "2021年9月",
    },
    "date-edu-master-end": {
      en: "Jun. 2024",
      zh: "2024年6月",
    },
    "date-edu-bachelor-start": {
      en: "Sep. 2017",
      zh: "2017年9月",
    },
    "date-edu-bachelor-end": {
      en: "Jun. 2021",
      zh: "2021年6月",
    },
    "education-phd-institution": {
      en: `<a href="https://www.nju.edu.cn/en/">Nanjing University</a> &amp; <a href="https://english.ia.cas.cn/">Institute of Automation, Chinese Academy of Sciences</a>`,
      zh: `<a href="https://www.nju.edu.cn/en/">南京大学</a> &amp; <a href="https://english.ia.cas.cn/">中国科学院自动化研究所</a>`,
    },
    "education-phd-program": {
      en: "Ph.D. Student in Computer Science and Engineering",
      zh: "计算机科学与技术专业 · 博士研究生",
    },
    "education-phd-mentors": {
      en: `Supervised by <a href="https://cs.nju.edu.cn/huojing/">Assoc. Prof. Jing Huo</a> and <a href="https://people.ucas.ac.cn/~yifanzhang">Prof. Yifan Zhang</a>`,
      zh: `导师：<a href="https://cs.nju.edu.cn/huojing/">霍静 副教授</a>、<a href="https://people.ucas.ac.cn/~yifanzhang">张一帆 教授</a>`,
    },
    "education-master-institution": {
      en: `<a href="https://www.nju.edu.cn/en/">Nanjing University</a>`,
      zh: `<a href="https://www.nju.edu.cn/en/">南京大学</a>`,
    },
    "education-master-program": {
      en: "M.Eng. in Control Science and Engineering",
      zh: "控制科学与工程专业 · 工学硕士",
    },
    "education-master-mentors": {
      en: `Advised by <a href="https://heyuanmingong.github.io/">Assoc. Prof. Zhi Wang</a> and <a href="https://ra.nju.edu.cn/szll/zzjs/20251120/i352846.html">Prof. Chunlin Chen</a>`,
      zh: `导师：<a href="https://heyuanmingong.github.io/">王志 副教授</a>、<a href="https://ra.nju.edu.cn/szll/zzjs/20251120/i352846.html">陈春林 教授</a>`,
    },
    "education-bachelor-institution": {
      en: `<a href="https://www.ecust.edu.cn/en/">East China University of Science and Technology</a>`,
      zh: `<a href="https://www.ecust.edu.cn/en/">华东理工大学</a>`,
    },
    "education-bachelor-program": {
      en: "B.Eng. in Mechanical Design, Manufacturing and Automation",
      zh: "机械设计制造及其自动化专业 · 工学学士",
    },
    "heading-internships": {
      en: "Internships",
      zh: "实习经历",
    },
    "date-intern-start": {
      en: "Jun. 2023",
      zh: "2023年6月",
    },
    "date-intern-end": {
      en: "Mar. 2024",
      zh: "2024年3月",
    },
    "internship-institution": {
      en: `<a href="https://tairos.tencent.com/">Tencent Robotics X Lab</a>`,
      zh: `<a href="https://tairos.tencent.com/">腾讯 Robotics X 实验室</a>`,
    },
    "internship-detail": {
      en: `Intern · Mentored by <a href="https://teaganli.github.io/">Tingguang Li</a>`,
      zh: `实习生 · 导师：<a href="https://teaganli.github.io/">李珽光</a>`,
    },
    "footer-updated": {
      en: "Last updated July 2026",
      zh: "最后更新于 2026 年 7 月",
    },
  };

  const root = document.documentElement;
  const languageButton = document.querySelector("#language-toggle");
  const themeButton = document.querySelector("#theme-toggle");
  const languageLabel = languageButton.querySelector(".site-control__language");

  function readPreference(key, fallback) {
    try {
      return window.localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  }

  function savePreference(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // The controls remain functional when storage is unavailable.
    }
  }

  function updateControlLabels() {
    const language = root.dataset.language;
    const theme = root.dataset.theme;
    const languageAction = language === "zh" ? "Switch to English" : "切换到中文";
    const themeAction = theme === "dark"
      ? (language === "zh" ? "切换到浅色模式" : "Switch to light mode")
      : (language === "zh" ? "切换到深色模式" : "Switch to dark mode");

    languageLabel.textContent = language === "zh" ? "EN" : "中";
    languageButton.setAttribute("aria-label", languageAction);
    languageButton.setAttribute("title", languageAction);
    languageButton.setAttribute("aria-pressed", String(language === "zh"));
    themeButton.setAttribute("aria-label", themeAction);
    themeButton.setAttribute("title", themeAction);
    themeButton.setAttribute("aria-pressed", String(theme === "dark"));
  }

  function applyLanguage(language, persist = true) {
    const nextLanguage = language === "zh" ? "zh" : "en";
    root.dataset.language = nextLanguage;
    root.lang = nextLanguage === "zh" ? "zh-CN" : "en";
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const entry = TRANSLATIONS[element.dataset.i18n];
      if (entry) {
        element.innerHTML = entry[nextLanguage];
      }
    });
    if (persist) {
      savePreference("hongyu-home:language", nextLanguage);
    }
    updateControlLabels();
  }

  function applyTheme(theme, persist = true) {
    const nextTheme = theme === "dark" ? "dark" : "light";
    root.dataset.theme = nextTheme;
    if (persist) {
      savePreference("hongyu-home:theme", nextTheme);
    }
    updateControlLabels();
  }

  languageButton.addEventListener("click", () => {
    applyLanguage(root.dataset.language === "zh" ? "en" : "zh");
  });

  themeButton.addEventListener("click", () => {
    applyTheme(root.dataset.theme === "dark" ? "light" : "dark");
  });

  applyTheme(readPreference("hongyu-home:theme", "light"), false);
  applyLanguage(readPreference("hongyu-home:language", "en"), false);
})();
