# 제3자 저작물

이 디렉터리는 rfpgen에 이식·번안한 외부 저작물의 원 라이선스와 고지문을 보관합니다. 이식 정책은 [설계서 11.2절](../docs/design.md), 분석은 [docs/analysis/chinese-bid-generators.md](../docs/analysis/chinese-bid-generators.md)를 보세요.

| 원 저장소 | 고정 커밋 | 라이선스 | 이 저장소에서 쓰는 곳 | 보관 파일 |
|---|---|---|---|---|
| [FB208/OpenBidKit_Yibiao](https://github.com/FB208/OpenBidKit_Yibiao) | `77a38f07db822daee0e4be80b84c2281c73d646e` | AGPL-3.0-only (+ §7(b) 저작자 귀속 고지) | `src/rfpgen/_third_party/agpl/openbidkit_yibiao/` — 작성지침·무효·감점 사유 추출 프롬프트 번안 | `OpenBidKit_Yibiao/LICENSE`, `OpenBidKit_Yibiao/NOTICE` |
| [guangshu100/BidMaster-Pro](https://github.com/guangshu100/BidMaster-Pro) | `cc89d9093651e3410f68384f926ceef672b76534` | AGPL-3.0 (README는 MIT로 표기 — LICENSE 파일 기준으로 AGPL로 취급) | 같은 위치 — 무효·감점 사유 프롬프트의 '실격 레드라인' 차원 | `BidMaster-Pro/LICENSE` |

AGPL에서 온 부분은 AGPL 조건을 계속 따릅니다. 이 프로그램을 네트워크 서비스(웹 UI·API)로 제공하면, 그 이용자에게 실행 중인 버전의 전체 대응 소스를 받을 수단을 제공해야 합니다(AGPL §13). OpenBidKit의 `NOTICE` 귀속 문구는 재배포본·수정본·대응 소스에 그대로 보존해야 합니다(AGPL §7(b)).
