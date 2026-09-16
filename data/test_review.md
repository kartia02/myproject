# PawNote 테스트셋 검수

각 행에서 발화·라벨·자연스러움을 확인한다. `OK` / `수정` / `제외` 중 하나를 적고,
수정·제외는 사유를 남긴다. 기준은 `labeling-guide.md` §7~§9이다.

## 001 — 2148 · multi

- 발화: 초코가 북어 반 그릇 엊그제 먹었음 아 진짜 잘 먹더라
- 라벨: `{"tool": "log_meal", "arguments": {"food": "북어", "amount": "반 그릇", "time": "엊그제", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 002 — 2347 · multi

- 발화: 구름이 오후에 공놀이 잠깐함
- 라벨: `{"tool": "log_activity", "arguments": {"activity_type": "play", "duration": "잠깐", "time": "오후"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 003 — 0038 · confusion

- 발화: 수의사한테 보여주려고 어제 거 다시 정리해뒀다
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "어제"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 004 — 2299 · multi

- 발화: 아, 우리 애 항문낭 다음에 언제쯤 챙겨야 되는지 궁금한데요.
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "anal_gland"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 005 — 2390 · multi

- 발화: 오늘 오전에 우리 강아지 양치 해줬다
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "teeth", "time": "오전", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 006 — 1630 · simple

- 발화: 양치 끝 치약 조금 남음 이빨 닦기 완료
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "teeth", "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 007 — 1300 · simple

- 발화: 습식 누나가 줫음
- 라벨: `{"tool": "log_meal", "arguments": {"food": "습식", "amount": null, "time": null, "caregiver": "누나"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 008 — 0938 · out_of_scope

- 발화: 초코 이 약 오늘 좀 줘도 되나?
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 009 — 1598 · simple

- 발화: 보리가 덴탈껌 하나 다 먹음
- 라벨: `{"tool": "log_meal", "arguments": {"food": "덴탈껌", "amount": null, "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 010 — 1716 · simple

- 발화: 콩이 닭가슴살 할아버지 줌
- 라벨: `{"tool": "log_meal", "arguments": {"food": "닭가슴살", "amount": null, "time": null, "caregiver": "할아버지"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 011 — 0107 · confusion

- 발화: 오늘 쉬를 봤습니다.
- 라벨: `{"tool": "log_excretion", "arguments": {"type": "urine", "condition": null, "time": "오늘"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 012 — 1245 · simple

- 발화: 오늘 양치 해줬다 생각보다 얌전했음
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "teeth", "time": "오늘", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 013 — 1118 · ambiguous

- 발화: 아까 먹은거랑 산책은 따로임
- 라벨: `{"tool": null, "arguments": {}, "reason": "ambiguous"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 014 — 1284 · simple

- 발화: 와 근데 저번주 화요일에 젤리 2.8킬로 나갓더라 진짜 요즘 들어 살이 찐 것도 같고 괜찮을까 싶다
- 라벨: `{"tool": "log_weight", "arguments": {"weight": "2.8킬로", "date": "저번주 화요일"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 015 — 1989 · multi

- 발화: 최근 일주일 우리 강아지 뭐뭐 했는지 정리좀 봐야겟어 병원 가는데 잘 말하러고
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "최근 일주일"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 016 — 2225 · multi

- 발화: 점심에 한 시간 반 동안 앉아 연습 진행했습니다.
- 라벨: `{"tool": "log_activity", "arguments": {"activity_type": "training", "duration": "한 시간 반", "time": "점심"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 017 — 2135 · multi

- 발화: 오늘 아침에 응가 봤는데 피가 조금 섞여 있었습니다.
- 라벨: `{"tool": "log_excretion", "arguments": {"type": "feces", "condition": "bloody", "time": "오늘 아침"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 018 — 1018 · out_of_scope

- 발화: 아 루비 간식 좀 떨어져서 그런지 닭가슴살 주문 해보고 싶은데 할아버지가 좋아할지 모르겠다
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 019 — 0071 · confusion

- 발화: 이틀 전 몽이 기록 정리 병원 가는데 요약 필요
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "이틀 전"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 020 — 0131 · confusion

- 발화: 밥을 안 먹어
- 라벨: `{"tool": "log_symptom", "arguments": {"symptom": "밥을 안 먹어", "severity": null, "time": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 021 — 0549 · confusion

- 발화: 아들 한테 넥스가드 줬다 얘 말하다 보니깐 약이 아니라 목욕 얘길 할 뻔 햇네
- 라벨: `{"tool": "log_medication", "arguments": {"name": "넥스가드", "dose": null, "time": null, "caregiver": "아들"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 022 — 1965 · multi

- 발화: 루비 몸무게 6키로 잴 때가 주말이었지
- 라벨: `{"tool": "log_weight", "arguments": {"weight": "6키로", "date": "주말"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 023 — 2395 · multi

- 발화: 내일 진료라 최근 일주일 기록 다시 한 번 정리해뒀다.
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "최근 일주일"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 024 — 1682 · simple

- 발화: 아 이번에 병원가는데 지난주애 어떤거 잇엇는지 다시 쵸메 해달라카고 보려구
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "지난주"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 025 — 1052 · out_of_scope

- 발화: 근데 오늘 날씨 뭐였어, 궁금하네
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 026 — 0792 · tense

- 발화: 얘 구충제 마지막으로 먹인 지 벌써 한 달 다 돼 가나? 이제 챙길 때 됐는지 신경 쓰이네
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "deworming"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 027 — 0004 · confusion

- 발화: 어제 밤에 쉬 질척한 거 한 번 쌌다
- 라벨: `{"tool": "log_excretion", "arguments": {"type": "urine", "condition": "soft", "time": "어제 밤"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 028 — 0069 · confusion

- 발화: 점심때 슬개골 영양제 우리 강아지 먹엿음
- 라벨: `{"tool": "log_medication", "arguments": {"name": "슬개골 영양제", "dose": null, "time": "점심때", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 029 — 0680 · tense

- 발화: 항문낭 한달 됐나 이제 할 차례인가
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "anal_gland"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 030 — 0775 · tense

- 발화: 몽이 양치 한지 좀 된 것 같은데 다음 차례 벌써 온 건가요?
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "teeth"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 031 — 0434 · confusion

- 발화: 오늘 아침에 구충제 챙겼다 오전 7시 반이었고 별 탈 없이 잘 먹였다
- 라벨: `{"tool": "log_medication", "arguments": {"name": "구충제", "dose": null, "time": "오전 7시 반", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 032 — 0286 · confusion

- 발화: 화요일에 오빠가 있었던 일 기억나세요?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "화요일", "until": "화요일", "caregiver": "오빠"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 033 — 2005 · multi

- 발화: 콩이 습식 싹 다 점심때 와이프가 줬습니다
- 라벨: `{"tool": "log_meal", "arguments": {"food": "습식", "amount": "싹 다", "time": "점심때", "caregiver": "와이프"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 034 — 0109 · confusion

- 발화: 달이 이번달 활동량 많아졋는지
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "activity", "period": "이번달"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 035 — 1332 · simple

- 발화: 초코 오늘은 평소보다 많이 물 마셨다 아들까지 봤다
- 라벨: `{"tool": "log_water", "arguments": {"amount": "평소보다 많이", "time": "오늘", "caregiver": "아들"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 036 — 1863 · multi

- 발화: 몽이 밤 10시 양치
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "teeth", "time": "밤 10시", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 037 — 0898 · tense

- 발화: 요즘 언니 뭐 했는지 봐야 함
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "요즘", "until": null, "caregiver": "언니"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 038 — 1869 · multi

- 발화: 계속 오전 삼촌 물마심
- 라벨: `{"tool": "log_water", "arguments": {"amount": "계속", "time": "오전", "caregiver": "삼촌"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 039 — 0276 · confusion

- 발화: 두부 피부약 동생이 오늘 발라ㅆ
- 라벨: `{"tool": "log_medication", "arguments": {"name": "피부약", "dose": null, "time": "오늘", "caregiver": "동생"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 040 — 1169 · ambiguous

- 발화: 까미 이거 언제였는지
- 라벨: `{"tool": null, "arguments": {}, "reason": "ambiguous"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 041 — 1430 · simple

- 발화: 콩이 오늘 발톱깎기 해줬다
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "nail", "time": "오늘", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 042 — 1010 · out_of_scope

- 발화: 지금 상황 위헙해 보이나 구별 잘 안됨
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 043 — 0907 · tense

- 발화: 최근 일주일에 아내 한테 무슨 일 있었는지 적혀있나?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "최근 일주일", "until": null, "caregiver": "아내"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 044 — 0643 · confusion

- 발화: 병원 가는데 엊그제 거 위주로 추려줘야 할 듯
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "엊그제"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 045 — 1768 · multi

- 발화: 아 근데 진짜 궁금한게, 우리 강아지 이번주에 물 먹은 게 지난주랑 비교해서 좀 늘었는지 줄었는지 혹시 알수있어? 음수량 한번 확인해주면 좋겠당~
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "water", "period": "이번주"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 046 — 1099 · ambiguous

- 발화: 음 이거 오늘 한 번 더 써야되나 싶기도 하고 아닌 거 같기도 하고 뭐가 맞는지 모르겠다
- 라벨: `{"tool": null, "arguments": {}, "reason": "ambiguous"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 047 — 1144 · ambiguous

- 발화: 방금 내용이 어떤 쪽에 들어가는지 헷갈려요
- 라벨: `{"tool": null, "arguments": {}, "reason": "ambiguous"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 048 — 2289 · multi

- 발화: 이틀 전에 아내가 양치 시켜줬다.
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "teeth", "time": "이틀 전", "caregiver": "아내"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 049 — 1825 · multi

- 발화: 오늘 오후 3시쯤 목욕시킴
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "bath", "time": "오후 3시", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 050 — 2283 · multi

- 발화: 젤리 삶은 계란 100g 자기 전 할머니
- 라벨: `{"tool": "log_meal", "arguments": {"food": "삶은 계란", "amount": "100g", "time": "자기 전", "caregiver": "할머니"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 051 — 1625 · simple

- 발화: 오늘 쉬 봤는데 피 조금 섞임
- 라벨: `{"tool": "log_excretion", "arguments": {"type": "urine", "condition": "bloody", "time": "오늘"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 052 — 0128 · confusion

- 발화: 2주간 기록 한 번 쭉 정리해둘까, 내일 병원 가는데 혹시 필요할 수도 있으니까
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "2주간"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 053 — 1132 · ambiguous

- 발화: 확인하러왓음ㅇ
- 라벨: `{"tool": null, "arguments": {}, "reason": "ambiguous"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 054 — 0566 · confusion

- 발화: 지난번엔 몸무게 기억이 잘 안 난다
- 라벨: `{"tool": "get_records", "arguments": {"record_type": "weight", "since": null, "until": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 055 — 0338 · confusion

- 발화: 할머니가 우리 아기 구충제 챙겨서 먹인거 그거 기록해야겟다
- 라벨: `{"tool": "log_medication", "arguments": {"name": "구충제", "dose": null, "time": null, "caregiver": "할머니"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 056 — 2357 · multi

- 발화: 달이가 오늘 오전에 물을 200ml이나 마셨다니까 깜짝 놀랐지 뭐야
- 라벨: `{"tool": "log_water", "arguments": {"amount": "200ml", "time": "오전", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 057 — 0852 · tense

- 발화: 심장사상충 약 지난 번에 먹인 지 좀 됐나 싶어서 그런데 다음 차례 언제쯤 챙겨야 되는 거야?
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "heartworm"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 058 — 2136 · multi

- 발화: 병원 가는데 지난주 기록 요약 필요
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "지난주"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 059 — 1953 · multi

- 발화: 엊그제 훈련 10분
- 라벨: `{"tool": "log_activity", "arguments": {"activity_type": "training", "duration": "10분", "time": "엊그제"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 060 — 1772 · multi

- 발화: 이상하게 오늘 밤에는 삼촌 있는 데서 댕댕이가 거의 안 물 마셨더라구요, 제가 옆에서 계속 봤었어요.
- 라벨: `{"tool": "log_water", "arguments": {"amount": "거의 안", "time": "밤", "caregiver": "삼촌"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 061 — 1206 · simple

- 발화: 목욕 9시쯤
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "bath", "time": "9시쯤", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 062 — 0460 · confusion

- 발화: 루비 배변이 엊그제랑 3일 전에도 언니가 챙긴 거 같은데 혹시 내가 빼먹은 기록 있나?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": "excretion", "since": "엊그제", "until": "3일 전", "caregiver": "언니"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 063 — 1624 · simple

- 발화: 콩이 계속 물 마셨다
- 라벨: `{"tool": "log_water", "arguments": {"amount": "계속", "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 064 — 2377 · multi

- 발화: 어제 밤에 강아지랑 10분 동안 장난감 갖고 놀았더니 강아지도 신났고 나도 기분 좋았다.
- 라벨: `{"tool": "log_activity", "arguments": {"activity_type": "play", "duration": "10분", "time": "어제 밤"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 065 — 0509 · confusion

- 발화: 어제 밤 계속 낑낑거려써
- 라벨: `{"tool": "log_symptom", "arguments": {"symptom": "낑낑거려", "severity": "severe", "time": "어제 밤"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 066 — 0439 · confusion

- 발화: 근데 혹시 어제 밤 투약 기록도 일주일째 맞지? 나 헷갈려서 그런데 혹시 내가 잘못본 건가 싶기도 하고~
- 라벨: `{"tool": "get_records", "arguments": {"record_type": "medication", "since": "일주일째", "until": "어제 밤", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 067 — 0344 · confusion

- 발화: 오늘은 할머니가 마루 심장사상충약 챙겨줬다.
- 라벨: `{"tool": "log_medication", "arguments": {"name": "심장사상충약", "dose": null, "time": "오늘", "caregiver": "할머니"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 068 — 2335 · multi

- 발화: 우리 아기 어제 30분 걷기
- 라벨: `{"tool": "log_activity", "arguments": {"activity_type": "walk", "duration": "30분", "time": "어제"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 069 — 0098 · confusion

- 발화: 화요일 거 뭐 있었는지 기억이 또 안 나네 화요일에 뭐 했지
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "화요일", "until": "화요일", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 070 — 0351 · confusion

- 발화: 막내 오늘 한 거 며칠 전하고 형이 한 거 알려주실 수 있나요?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "오늘", "until": "며칠 전", "caregiver": "형"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 071 — 0645 · confusion

- 발화: 우리 개 한 달 남편이 한 거 있지 기억나?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "한 달", "until": null, "caregiver": "남편"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 072 — 2050 · multi

- 발화: 오늘 아침에 3.4킬로였써용 오타났지만 숫자는 맞음
- 라벨: `{"tool": "log_weight", "arguments": {"weight": "3.4킬로", "date": "오늘 아침"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 073 — 0353 · confusion

- 발화: 요즘 강아지 산책 더 많아진 것 같지 않아, 나만 그렇게 느끼나 싶네, 활동량도 전보다 늘었는지 궁금해서 말이지, 활력도 좀 달라진 거 같고 그렇거든
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "activity", "period": "요즘"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 074 — 0409 · confusion

- 발화: 3일 전 넥스가드 두 방울 준거 니가 기억하냐 난 헷갈리네
- 라벨: `{"tool": "log_medication", "arguments": {"name": "넥스가드", "dose": "두 방울", "time": "3일 전", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 075 — 2125 · multi

- 발화: 이틀 전 브러싱함 좀 빠르게 했음
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "brushing", "time": "이틀 전", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 076 — 0896 · tense

- 발화: 이번주 삼촌 있었던 일 볼 수 있을까요?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "이번주", "until": null, "caregiver": "삼촌"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 077 — 0272 · confusion

- 발화: 지난번 산책 기록 다시 보고 싶네
- 라벨: `{"tool": "get_records", "arguments": {"record_type": "activity", "since": null, "until": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 078 — 0970 · out_of_scope

- 발화: 산책 달이 품종 뭐엿지
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 079 — 1966 · multi

- 발화: 점심에 오빠가 물을 거의 안 마셨어요.
- 라벨: `{"tool": "log_water", "arguments": {"amount": "거의 안", "time": "점심", "caregiver": "오빠"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 080 — 0623 · confusion

- 발화: 강아지 밥 먹는 양이 한 달 기준으로 더 늘었나요, 줄었나요?
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "meal", "period": "한 달"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 081 — 2359 · multi

- 발화: 병원 가는데 어제 기록만 확인할 수 있나요?
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "어제"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 082 — 0208 · confusion

- 발화: 회충약 한 알 아침에먹임
- 라벨: `{"tool": "log_medication", "arguments": {"name": "회충약", "dose": "한 알", "time": "아침", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 083 — 0922 · out_of_scope

- 발화: 병원 예약
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 084 — 0654 · confusion

- 발화: 2주간 누나 배변
- 라벨: `{"tool": "get_records", "arguments": {"record_type": "excretion", "since": "2주간", "until": null, "caregiver": "누나"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 085 — 1305 · simple

- 발화: 오늘 물 거의 안마셧어
- 라벨: `{"tool": "log_water", "arguments": {"amount": "거의 안", "time": "오늘", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 086 — 2295 · multi

- 발화: 루비가 자기 전 대변 봤는데 혈변처럼 붉은 게 섞임 한번 확인해봤어
- 라벨: `{"tool": "log_excretion", "arguments": {"type": "feces", "condition": "bloody", "time": "자기 전"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 087 — 1452 · simple

- 발화: 아 나 갑자기 남편이 오늘 목욕 시켰다 그러더라
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "bath", "time": "오늘", "caregiver": "남편"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 088 — 1641 · simple

- 발화: 댕댕이 오리목뼈 먹었다
- 라벨: `{"tool": "log_meal", "arguments": {"food": "오리목뼈", "amount": null, "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 089 — 1005 · out_of_scope

- 발화: 보리 간식 떨어졌는데 어디서 사면 괜찮을지 혹시 알아?
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 090 — 1888 · multi

- 발화: 두부 어제 밤에 귀 청소 아들이 했어요
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "ear", "time": "어제 밤", "caregiver": "아들"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 091 — 0547 · confusion

- 발화: 산책 어땠는지 줄었는지 늘었는지
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "activity", "period": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 092 — 1650 · simple

- 발화: 오늘 300미리 마셨구나 오빠가
- 라벨: `{"tool": "log_water", "arguments": {"amount": "300미리", "time": "오늘", "caregiver": "오빠"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 093 — 0693 · tense

- 발화: 어제 엄마가 3일 전 뭐 했는지 혹시 기억나?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "3일 전", "until": "어제", "caregiver": "엄마"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 094 — 2182 · multi

- 발화: 우리 애가 배를 자꾸 핥아 꽤 심하게 새벽에 그랬슴다
- 라벨: `{"tool": "log_symptom", "arguments": {"symptom": "배를 자꾸 핥아", "severity": "moderate", "time": "새벽"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 095 — 0895 · tense

- 발화: 항문낭한지 꽤 된 것같은데 이제쯤 해줘야 할까?
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "anal_gland"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 096 — 2149 · multi

- 발화: 병원 가는데 지난주 기록 정리해서 보여드릴까 합니다
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "지난주"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 097 — 2208 · multi

- 발화: 우리 애 4킬로 800 주말
- 라벨: `{"tool": "log_weight", "arguments": {"weight": "4킬로 800", "date": "주말"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 098 — 1508 · simple

- 발화: 3.4킬로 나간 거 며칠 전 기록해둠
- 라벨: `{"tool": "log_weight", "arguments": {"weight": "3.4킬로", "date": "며칠 전"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 099 — 2317 · multi

- 발화: 오늘 아침 8시에 잠깐 우리 애랑 외출했지 뭐야.
- 라벨: `{"tool": "log_activity", "arguments": {"activity_type": "outing", "duration": "잠깐", "time": "아침 8시"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 100 — 0290 · confusion

- 발화: 구름이 지난 한 달 증상 많아졌나 궁금해
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "symptom", "period": "지난 한 달"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 101 — 1381 · simple

- 발화: 우리 개 고구마 잠깐 전에 먹음
- 라벨: `{"tool": "log_meal", "arguments": {"food": "고구마", "amount": null, "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 102 — 1357 · simple

- 발화: 그러니까 오늘 낮에 한참 있다가 한 그릇 다 마셨네 물도 안 남기고
- 라벨: `{"tool": "log_water", "arguments": {"amount": "한 그릇", "time": "오늘", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 103 — 1288 · simple

- 발화: 룸메가 한 그릇 물을 마셨습니다.
- 라벨: `{"tool": "log_water", "arguments": {"amount": "한 그릇", "time": null, "caregiver": "룸메"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 104 — 1049 · out_of_scope

- 발화: 말티즈 털 관리 힘든편이냐 누구 알아?
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 105 — 0908 · tense

- 발화: 발톱 지난번에 자른 지 좀 된 거 같은데 이제 다 자랐으려나, 한 번 확인해봐야겠다
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "nail"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 106 — 0203 · confusion

- 발화: 엊그제 산책 기록언 어디쯤있나 아직못찾겠네;
- 라벨: `{"tool": "get_records", "arguments": {"record_type": "activity", "since": "엊그제", "until": "엊그제", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 107 — 1843 · multi

- 발화: 이번주에 있었던 일 정리해서 병원 가는데 보여드리려고 합니다
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "이번주"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 108 — 1564 · simple

- 발화: 구름이 건사료 와이프가 줬음
- 라벨: `{"tool": "log_meal", "arguments": {"food": "건사료", "amount": null, "time": null, "caregiver": "와이프"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 109 — 1468 · simple

- 발화: 캔 오늘 할머니 손에서 먹음
- 라벨: `{"tool": "log_meal", "arguments": {"food": "캔", "amount": null, "time": "오늘", "caregiver": "할머니"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 110 — 0292 · confusion

- 발화: 엊그제 꽤 축 처져 있어
- 라벨: `{"tool": "log_symptom", "arguments": {"symptom": "축 처져 있어", "severity": "moderate", "time": "엊그제"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 111 — 0382 · confusion

- 발화: 우리 강아지 몸무게 요즘 늘었냐
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "weight", "period": "요즘"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 112 — 1326 · simple

- 발화: 반 그릇 마심
- 라벨: `{"tool": "log_water", "arguments": {"amount": "반 그릇", "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 113 — 0244 · confusion

- 발화: 아 병원 가는데 어제 기록 정리 좀 해와야겠네
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "어제"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 114 — 2229 · multi

- 발화: 황태 싹 다 오후 3시 젤리 아들
- 라벨: `{"tool": "log_meal", "arguments": {"food": "황태", "amount": "싹 다", "time": "오후 3시", "caregiver": "아들"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 115 — 1351 · simple

- 발화: 달이가 200ml를 마셨습니다
- 라벨: `{"tool": "log_water", "arguments": {"amount": "200ml", "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 116 — 0296 · confusion

- 발화: 일주일째 활동량 변함 있나
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "activity", "period": "일주일째"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 117 — 0815 · tense

- 발화: 어제 언니 뭐 했더라 다시 봐야겠다.
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "어제", "until": "어제", "caregiver": "언니"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 118 — 1093 · ambiguous

- 발화: 근데 얘가 어제랑 오늘 뭐가 달랐는지 한번만 다시 생각해봐야겠다
- 라벨: `{"tool": null, "arguments": {}, "reason": "ambiguous"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 119 — 1992 · multi

- 발화: 이틀 전 좀 심하게 자꾸 긁어ㅛ
- 라벨: `{"tool": "log_symptom", "arguments": {"symptom": "자꾸 긁어", "severity": "moderate", "time": "이틀 전"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 120 — 2219 · multi

- 발화: 요 며칠 증상 많아진 거야
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "symptom", "period": "요 며칠"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 121 — 2378 · multi

- 발화: 저녁 7시에 할머니가 콩이 평소보다 많이 물 마셨다고 알려주셨어요
- 라벨: `{"tool": "log_water", "arguments": {"amount": "평소보다 많이", "time": "저녁 7시", "caregiver": "할머니"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 122 — 0235 · confusion

- 발화: 오늘 아침이랑 며칠 전에 한 번 봐줄수잇어?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "며칠 전", "until": "오늘 아침", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 123 — 1012 · out_of_scope

- 발화: 오늘 기온 좀 알려주시면 좋겠어요
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 124 — 0298 · confusion

- 발화: 이번주 식사량줄어드었는지 늘엇는지보여줄수있나
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "meal", "period": "이번주"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 125 — 0090 · confusion

- 발화: 남편이 항생제 챙겨줬다고 하더라
- 라벨: `{"tool": "log_medication", "arguments": {"name": "항생제", "dose": null, "time": null, "caregiver": "남편"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 126 — 2020 · multi

- 발화: 루비 물 일주일째 늘었는지 줄었는지 혹시 알 수 있나?
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "water", "period": "일주일째"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 127 — 1531 · simple

- 발화: 딸 거의 안 마심
- 라벨: `{"tool": "log_water", "arguments": {"amount": "거의 안", "time": null, "caregiver": "딸"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 128 — 2072 · multi

- 발화: 아빠 오전 한 그릇 물 마심
- 라벨: `{"tool": "log_water", "arguments": {"amount": "한 그릇", "time": "오전", "caregiver": "아빠"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 129 — 2132 · multi

- 발화: 요즘 밥 먹는 양 변한거 있나?
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "meal", "period": "요즘"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 130 — 1525 · simple

- 발화: 아 진짜 오늘은 우리 강아지가 간식 챙겨 먹은 시간이 오후 3시였나 아들도 있었고 이게 다행인 건지 모르겠다
- 라벨: `{"tool": "log_meal", "arguments": {"food": "간식", "amount": null, "time": "오후 3시", "caregiver": "아들"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 131 — 2032 · multi

- 발화: 어제 보리 응가 무름엿
- 라벨: `{"tool": "log_excretion", "arguments": {"type": "feces", "condition": "soft", "time": "어제"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 132 — 2055 · multi

- 발화: 점심때 침을 많이 흘려 좀 심하게
- 라벨: `{"tool": "log_symptom", "arguments": {"symptom": "침을 많이 흘려", "severity": "moderate", "time": "점심때"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 133 — 0358 · confusion

- 발화: 2주간 이모 이틀 전 기억나나
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "2주간", "until": "이틀 전", "caregiver": "이모"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 134 — 1324 · simple

- 발화: 이틀 전엔 몸무게가 12kg 찍혔네
- 라벨: `{"tool": "log_weight", "arguments": {"weight": "12kg", "date": "이틀 전"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 135 — 1075 · out_of_scope

- 발화: 까미 털빠지는게 평소 보다 더 심할때 원랜 품종 때문인건가?
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 136 — 0399 · confusion

- 발화: 심장사상충 약 챙김 바쁘네
- 라벨: `{"tool": "log_medication", "arguments": {"name": "심장사상충 약", "dose": null, "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 137 — 0778 · tense

- 발화: 막내 목욕 지난번에 하고 꽤 된 거 같은데 벌써 한 달 넘은 거 아냐?
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "bath"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 138 — 1014 · out_of_scope

- 발화: 우리 강아지에게 맞는 사료 추천해주실 수 있을까요?
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 139 — 1496 · simple

- 발화: 산책 갔다왓어
- 라벨: `{"tool": "log_activity", "arguments": {"activity_type": "walk", "duration": null, "time": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 140 — 0275 · confusion

- 발화: 병원 가는데 이번달 기록 한 번 쭉 보고 가야지 싶더라
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "이번달"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 141 — 2049 · multi

- 발화: 3일 전 기록 쫌 볼래 내일 병원 가는거 알아야대서
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "3일 전"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 142 — 0889 · tense

- 발화: 토요일 아침에 뭐 했는지 기억나요?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "토요일 아침", "until": "토요일 아침", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 143 — 1938 · multi

- 발화: 막내 3일 전 계속 아내 물 마심
- 라벨: `{"tool": "log_water", "arguments": {"amount": "계속", "time": "3일 전", "caregiver": "아내"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 144 — 0030 · confusion

- 발화: 3일 전에 응가 했습니다
- 라벨: `{"tool": "log_excretion", "arguments": {"type": "feces", "condition": null, "time": "3일 전"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 145 — 1202 · simple

- 발화: 요거트 줘씀
- 라벨: `{"tool": "log_meal", "arguments": {"food": "요거트", "amount": null, "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 146 — 1649 · simple

- 발화: 강아지 증상 요즘 어떤지 변한 거 있나?
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "symptom", "period": "요즘"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 147 — 2061 · multi

- 발화: 배변이 한 달에 늘었는지 줄었는지 아는 사람 있나
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "excretion", "period": "한 달"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 148 — 0226 · confusion

- 발화: 재채기 자기 전
- 라벨: `{"tool": "log_symptom", "arguments": {"symptom": "재채기", "severity": null, "time": "자기 전"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 149 — 0598 · confusion

- 발화: 몽이 쉬
- 라벨: `{"tool": "log_excretion", "arguments": {"type": "urine", "condition": null, "time": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 150 — 1246 · simple

- 발화: 호두 한 줌 먹였음
- 라벨: `{"tool": "log_meal", "arguments": {"food": null, "amount": "한 줌", "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 151 — 1204 · simple

- 발화: 오늘 우리 애기 아빠 많이 물 마신듯
- 라벨: `{"tool": "log_water", "arguments": {"amount": "많이", "time": "오늘", "caregiver": "우리 애기 아빠"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 152 — 1467 · simple

- 발화: 5킬로 200 측정
- 라벨: `{"tool": "log_weight", "arguments": {"weight": "5킬로 200", "date": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 153 — 0798 · tense

- 발화: 까미 구충제 이제 챙길 때 됐나
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "deworming"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 154 — 0089 · confusion

- 발화: 한 달 배변 줄었는지
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "excretion", "period": "한 달"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 155 — 1196 · ambiguous

- 발화: 달이 아까 교육 했는지 훈련 맞는지 애매
- 라벨: `{"tool": null, "arguments": {}, "reason": "ambiguous"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 156 — 0055 · confusion

- 발화: 얘 병원 가야 돼서 저저번주 거 뭐 있었는지 혹시 기억나?
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "저저번주"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 157 — 0520 · confusion

- 발화: 와이프 몸무게 최근 거 뭐로 되어있지?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": "weight", "since": "최근", "until": null, "caregiver": "와이프"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 158 — 2279 · multi

- 발화: 어제 밤 확인할거 병원 가는데 챙겨야함
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "어제 밤"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 159 — 0475 · confusion

- 발화: 넥스가드 한 스푼 누나
- 라벨: `{"tool": "log_medication", "arguments": {"name": "넥스가드", "dose": "한 스푼", "time": null, "caregiver": "누나"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 160 — 0917 · out_of_scope

- 발화: 근처 동물병원 예약하는거 이거 아는사람 있나?
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 161 — 2120 · multi

- 발화: 정오에 저녁밥으로 80그램을 아빠가 챙겨줬다.
- 라벨: `{"tool": "log_meal", "arguments": {"food": "저녁밥", "amount": "80그램", "time": "정오", "caregiver": "아빠"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 162 — 0857 · tense

- 발화: 몽이 하트가드 준 지 벌써 한 달 넘엇나 다음 타임 챙겨야 하는 시점인지 좀 헷갈
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "heartworm"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 163 — 0994 · out_of_scope

- 발화: 까미 엉청 귀여운데 오늘왠지 좀 더 말앙한ㄷ?
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 164 — 1942 · multi

- 발화: 아 맞다, 몽이 점심때 응가 정상이라고 하더라구, 그냥 참고하려구 말해봤어
- 라벨: `{"tool": "log_excretion", "arguments": {"type": "feces", "condition": "normal", "time": "점심때"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 165 — 0508 · confusion

- 발화: 참 엄마가 점심때 달이 안약 준 거 얘기했나
- 라벨: `{"tool": "log_medication", "arguments": {"name": "안약", "dose": null, "time": "점심때", "caregiver": "엄마"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 166 — 2253 · multi

- 발화: 발톱 엊그제 딸
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "nail", "time": "엊그제", "caregiver": "딸"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 167 — 2144 · multi

- 발화: 오늘 우리 아기가 좀 심하게 몸을 웅크려 있었네, 갑자기 그래서 좀 걱정도 되고 그렇더라고
- 라벨: `{"tool": "log_symptom", "arguments": {"symptom": "몸을 웅크려", "severity": "moderate", "time": "오늘"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 168 — 1688 · simple

- 발화: 며칠 전 엄마가 챙겨준 사료 잘 먹었다
- 라벨: `{"tool": "log_meal", "arguments": {"food": "사료", "amount": null, "time": "며칠 전", "caregiver": "엄마"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 169 — 0774 · tense

- 발화: 구충제 한 지 벌써 한 달 넘은 거 아님 우리 아기
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "deworming"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 170 — 1701 · simple

- 발화: 오늘은 우리 아기 털 빗기 해줬어요.
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "brushing", "time": "오늘", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 171 — 2036 · multi

- 발화: 일주일째 배변 양이 늘었는지 궁금하다.
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "excretion", "period": "일주일째"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 172 — 1850 · multi

- 발화: 점심때 아들이 반 그릇 정도 물 마셨습니다
- 라벨: `{"tool": "log_water", "arguments": {"amount": "반 그릇", "time": "점심때", "caregiver": "아들"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 173 — 0848 · tense

- 발화: 마루 백신 한 달 됐나 이제 다시 맞힐 때인가
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "vaccine"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 174 — 1471 · simple

- 발화: 귀 닦기 아빠 했음
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "ear", "time": null, "caregiver": "아빠"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 175 — 0320 · confusion

- 발화: 병원 가는데 지난주 일 얼추 정리해두면 좋겠지
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "지난주"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 176 — 0046 · confusion

- 발화: 근데 2주간 활동량 그거 좀 달라진 거 같기도 하지 않아
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "activity", "period": "2주간"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 177 — 1534 · simple

- 발화: 발톱은 삼촌이 했습니다
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "nail", "time": null, "caregiver": "삼촌"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 178 — 0644 · confusion

- 발화: 요 며칠 우리 아이 어떻게 지냈는지 병원에 가서 말씀드리려고 한 번 정리하고 싶어요.
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "요 며칠"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 179 — 1847 · multi

- 발화: 이틀 전 룸메랑 발톱깎기 해줬다 우리 애 진짜 가만히 안있더라
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "nail", "time": "이틀 전", "caregiver": "룸메"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 180 — 2386 · multi

- 발화: 몽이 2주간 산책 추이 바뀐 거 있냐 이거 좀 신경 쓰여서 말이야
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "activity", "period": "2주간"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 181 — 1565 · simple

- 발화: 목욕했엇는데 물이 좀따뜻했음
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "bath", "time": null, "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 182 — 2271 · multi

- 발화: 이번주 식욕 좀 달라졌나 싶다
- 라벨: `{"tool": "get_trend", "arguments": {"metric": "meal", "period": "이번주"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 183 — 0070 · confusion

- 발화: 종합 영양제 한 스푼 아침줘씀
- 라벨: `{"tool": "log_medication", "arguments": {"name": "종합 영양제", "dose": "한 스푼", "time": "아침", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 184 — 2026 · multi

- 발화: 아침에 발톱깎기 했는대 진짜 발톱이 너무 빨리 자라는 느낌임
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "nail", "time": "아침", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 185 — 1363 · simple

- 발화: 강아지 오늘 애견운동장 다녀왔어요
- 라벨: `{"tool": "log_activity", "arguments": {"activity_type": "outing", "duration": null, "time": "오늘"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 186 — 0563 · confusion

- 발화: 며칠 전 엄마가 종합 영양제 한 번 줬다
- 라벨: `{"tool": "log_medication", "arguments": {"name": "종합 영양제", "dose": "한 번", "time": "며칠 전", "caregiver": "엄마"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 187 — 2196 · multi

- 발화: 오늘 아침에 한 거 정리해뒀지, 곧 병원 가야 해서 혹시 필요할까 싶어서
- 라벨: `{"tool": "get_vet_summary", "arguments": {"since": "오늘 아침"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 188 — 1309 · simple

- 발화: 할아버지 아침 8시 브러싱했음
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "brushing", "time": "아침 8시", "caregiver": "할아버지"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 189 — 1767 · multi

- 발화: 발톱 저녁 7시깎음 깜박할뻔햇
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "nail", "time": "저녁 7시", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 190 — 1219 · simple

- 발화: 오늘은 산책 끝나고 앉아 연습 했습니다
- 라벨: `{"tool": "log_activity", "arguments": {"activity_type": "training", "duration": null, "time": "오늘"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 191 — 0724 · tense

- 발화: 토요일 아침에 뭐 했었나?
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "토요일 아침", "until": "토요일 아침", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 192 — 1414 · simple

- 발화: 달이 오늘 정오에 목욕함 나 힘들어서 죽을 뻔
- 라벨: `{"tool": "log_care", "arguments": {"care_type": "bath", "time": "정오", "caregiver": null}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 193 — 1103 · ambiguous

- 발화: 이번주에 음수량 요애 봐야겠는ㄴ데 좀 늘엇나 물 좀 줄엇나 헷갈리넹?
- 라벨: `{"tool": null, "arguments": {}, "reason": "ambiguous"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 194 — 0872 · tense

- 발화: 구충제 마지막으로 준 지 벌써 한 달 넘은 거 아니지
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "deworming"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 195 — 1844 · multi

- 발화: 아침 8시 소변 무름
- 라벨: `{"tool": "log_excretion", "arguments": {"type": "urine", "condition": "soft", "time": "아침 8시"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 196 — 1223 · simple

- 발화: 저녁 7시에 우리 애기 아빠가 물 마신 거 봤어요
- 라벨: `{"tool": "log_water", "arguments": {"amount": null, "time": "저녁 7시", "caregiver": "우리 애기 아빠"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 197 — 0321 · confusion

- 발화: 요즘 누나가 콩이 돌봐준 기록 있지 지난 한 달 거 다시 한번 확인 좀 할라고
- 라벨: `{"tool": "get_records", "arguments": {"record_type": null, "since": "지난 한 달", "until": null, "caregiver": "누나"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 198 — 0885 · tense

- 발화: 달이 심장사상충 약 지난번 하고 이제 또 챙겨야 할 때인가 싶네
- 라벨: `{"tool": "get_care_due", "arguments": {"care_type": "heartworm"}, "reason": null}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 199 — 1076 · out_of_scope

- 발화: 우리 애 이런 증상 있으면 위험한 거야?
- 라벨: `{"tool": null, "arguments": {}, "reason": "out_of_scope"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:

## 200 — 1131 · ambiguous

- 발화: 이거 우리 애한테 했나?
- 라벨: `{"tool": null, "arguments": {}, "reason": "ambiguous"}`
- 판정: [ ] OK  [ ] 수정  [ ] 제외
- 사유 / 수정안:
