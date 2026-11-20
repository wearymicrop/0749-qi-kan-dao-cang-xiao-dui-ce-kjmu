from app.errors import LedgerError


def claim_issues(numbers, expected):
    if expected is None:
        raise LedgerError("OUT_OF_ORDER", "该年度不在订购规则内")
    if numbers["volume"] != expected["volume"]:
        raise LedgerError("WRONG_VOLUME", "来刊卷号与订购规则冲突")
    if numbers["kind"] == "supplement":
        return []
    if numbers["first"] < expected["first"] or numbers["last"] > expected["last"]:
        raise LedgerError("OUTSIDE_RANGE", "期号越出本卷，不拆分采信")
    return list(range(numbers["first"], numbers["last"] + 1))


def claim_cross_year(numbers, note, years):
    """跨年度合期只能整体采信：说明年度、登记卷号、范围全部吻合，否则整条隔离。"""
    if numbers["kind"] == "supplement":
        raise LedgerError("NOTE_MISMATCH", "增刊不得引用跨年度出版说明")
    if len(note["years"]) != len(years) or note["years"] != [item["year"] for item in years]:
        raise LedgerError("NOTE_MISMATCH", "来刊引用的出版说明年度与登记年度不符")
    # 登记卷号取合期起始卷；其余卷由出版说明本身界定，避免让一个实物背两个卷号
    if numbers["volume"] != years[0]["volume"]:
        raise LedgerError("NOTE_MISMATCH", "跨年度合期登记卷号与出版说明起始卷不符")
    if years[0]["numbering"] == "continuous":
        # 连排期号跨年唯一：合期只占说明声明的两个边界期位（末年号→次年初号）
        if numbers["first"] != years[0]["last"] or numbers["last"] != years[-1]["first"]:
            raise LedgerError("NOTE_MISMATCH", "跨年度合期须覆盖末年号与次年初号，不拆分采信")
    else:
        # 逐年复位：登记为末年号倒接首年号（如 4-1），两端各自对准本卷边界
        if numbers["first"] != years[0]["last"] or numbers["last"] != years[-1]["first"]:
            raise LedgerError("NOTE_MISMATCH", "跨年度合期须从末年号接至首年号，与出版说明卷界不符")
    # 一件实物只挂说明声明的两个边界期位，绝不吞掉卷内其他期位
    return [
        {"chain": note["chain"], "year": years[0]["year"], "volume": years[0]["volume"],
         "issues": [years[0]["last"]]},
        {"chain": note["chain"], "year": years[-1]["year"], "volume": years[-1]["volume"],
         "issues": [years[-1]["first"]]},
    ]
