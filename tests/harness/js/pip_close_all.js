const wins = [...Services.wm.getEnumerator("Toolkit:PictureInPicture")];
for (const w of wins) w.close();
await new Promise(r => setTimeout(r, 800));
return { closed: wins.length, left: [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].length };
