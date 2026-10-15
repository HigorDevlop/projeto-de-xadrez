"""A oficina reage apenas a tentativas validadas pelo servidor."""
import streamlit as st
from pathlib import Path
from media_assets import asset_source


_FORGE = st.components.v2.component(
    'tactics_forge',
    html='''<section class="forge" aria-label="Oficina tática">
    <video muted playsinline preload="auto" aria-label="Ferreiro fotorrealista trabalhando com espada e bigorna"></video>
    <p class="smith-comment" role="status" aria-live="polite"></p>
    <div class="blade-meter"><span>Fio da lâmina</span><strong></strong></div>
    <progress max="100" value="0" aria-label="Fio da lâmina"></progress></section>''',
    css='''
      .forge {border:1px solid var(--border);border-radius:14px;padding:20px;background:var(--surface);
        color:var(--ink);font:15px/1.65 'Segoe UI',system-ui,sans-serif;margin-bottom:20px}
      video {display:block;width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:9px;background:#111a16}
      .smith-comment {min-height:48px;margin:12px 0}
      .blade-meter {display:flex;justify-content:space-between;font-size:12px;color:var(--muted)}
      progress {width:100%;height:7px;appearance:none;border:0;border-radius:8px;overflow:hidden;background:var(--workshop)}
      progress::-webkit-progress-bar {background:var(--workshop)}
      progress::-webkit-progress-value {background:#b48747;transition:width .3s}
    ''',
    js='''export default function({data,parentElement}){
      const host=parentElement.host ?? parentElement,forge=parentElement.querySelector('.forge');
      const palette=data.dark?['#1A2720','#EDF3ED','#ACBCAF','#354A3C','#223329']:['#FFFEFA','#202B26','#626F66','#D9DED5','#ECEFE8'];
      ['--surface','--ink','--muted','--border','--workshop'].forEach((key,i)=>host.style.setProperty(key,palette[i]));
      const motivation=[
        'Belo lance! Sua visão está ficando mais afiada a cada desafio.',
        'Muito bem! Paciência e cálculo transformam boas ideias em grandes jogadas.',
        'Você encontrou o caminho! Continue observando cada detalhe da posição.',
        'Golpe certeiro! Confie no seu cálculo e siga em frente.',
        'Excelente trabalho! Cada acerto fortalece o seu xadrez.',
        'É assim que se evolui: atenção, treino e um bom lance de cada vez.',
        'Boa leitura do tabuleiro! Leve essa concentração para o próximo desafio.',
        'Continue firme! A prática de hoje prepara as vitórias de amanhã.'
      ];
      const success=['correct','progress','recovered'].includes(data.result);
      if(parentElement._phraseEvent!==data.event){
        parentElement._phraseEvent=data.event;
        if(success && data.event>0){
          if(window.__forgePhrase?.event!==data.event){
            const index=window.__forgePhraseIndex ?? 0;
            window.__forgePhrase={event:data.event,text:motivation[index%motivation.length]};
            window.__forgePhraseIndex=index+1;
          }
          parentElement._phrase=window.__forgePhrase.text;
        }
      }
      const comments={idle:'A forja está pronta. Resolva o tático para afiar sua espada.',
        correct:parentElement._phrase,
        wrong:'A espada foi prejudicada por esse golpe. Este exercício não concederá afiação. Reveja a posição.',
        recovered:(parentElement._phrase || 'Você concluiu o desafio!')+' Sem afiação: houve erro ou este desafio já foi recompensado.',
        progress:parentElement._phrase};
      parentElement.querySelector('.smith-comment').textContent=comments[data.result] ?? comments.idle;
      parentElement.querySelector('progress').value=data.sharpness;
      parentElement.querySelector('strong').textContent=data.sharpness+'%';
      forge.dataset.result=data.result;
      const video=parentElement.querySelector('video');
      if(!video.getAttribute('src')){video.src=data.source;video.poster=data.poster;}
      if(!data.speak && 'speechSynthesis' in window)speechSynthesis.cancel();
      if(parentElement._forgeEvent===data.event)return;
      parentElement._forgeEvent=data.event;
      if(success && data.event>0 && data.speak && 'speechSynthesis' in window && window.__forgeSpoken!==data.event){
        window.__forgeSpoken=data.event;
        const speech=new SpeechSynthesisUtterance(parentElement._phrase);speech.lang='pt-BR';speech.rate=.96;
        const voice=speechSynthesis.getVoices().find(v=>v.lang==='pt-BR');if(voice)speech.voice=voice;
        speechSynthesis.cancel();speechSynthesis.speak(speech);
      }
      if(data.result==='correct' && data.event>0 && window.__forgePlayed!==data.event && !window.matchMedia('(prefers-reduced-motion: reduce)').matches){
        window.__forgePlayed=data.event;video.currentTime=0;video.play().catch(()=>{});
      }
    }''',
)


def tactics_forge(event, result, sharpness, dark=False, speak=True):
    assets = Path(__file__).parent / 'assets'
    video, poster = assets / 'forge-photoreal.mp4', assets / 'forge-photoreal-poster.jpg'
    _FORGE(data={'event': event, 'result': result, 'sharpness': sharpness, 'dark': dark, 'speak': speak,
                 'source': asset_source(str(video), video.stat().st_mtime_ns),
                 'poster': asset_source(str(poster), poster.stat().st_mtime_ns)}, key='tactics_forge')
