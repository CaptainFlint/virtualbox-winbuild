/* $Id: bs3-cmn-MemPCpy.c $ */
/** @file
 * BS3Kit - Bs3MemPCpy
 */

/*
 * Copyright (C) 2007-2020 Oracle Corporation
 *
 * This file is part of VirtualBox Open Source Edition (OSE), as
 * available from http://www.virtualbox.org. This file is free software;
 * you can redistribute it and/or modify it under the terms of the GNU
 * General Public License (GPL) as published by the Free Software
 * Foundation, in version 2 as it comes in the "COPYING" file of the
 * VirtualBox OSE distribution. VirtualBox OSE is distributed in the
 * hope that it will be useful, but WITHOUT ANY WARRANTY of any kind.
 *
 * The contents of this file may alternatively be used under the terms
 * of the Common Development and Distribution License Version 1.0
 * (CDDL) only, as it comes in the "COPYING.CDDL" file of the
 * VirtualBox OSE distribution, in which case the provisions of the
 * CDDL are applicable instead of those of the GPL.
 *
 * You may elect to license modified versions of this file under the
 * terms and conditions of either the GPL or the CDDL or both.
 */

#include "bs3kit-template-header.h"

#undef Bs3MemPCpy
BS3_CMN_DEF(void BS3_FAR *, Bs3MemPCpy,(void BS3_FAR *pvDst, const void BS3_FAR *pvSrc, size_t cbToCopy))
{
    size_t          cLargeRounds;
    BS3CPTRUNION    uSrc;
    BS3PTRUNION     uDst;
    uSrc.pv = pvSrc;
    uDst.pv = pvDst;

    cLargeRounds = cbToCopy / sizeof(*uSrc.pcb);
    while (cLargeRounds-- > 0)
        *uDst.pcb++ = *uSrc.pcb++;

    cbToCopy %= sizeof(*uSrc.pcb);
    while (cbToCopy-- > 0)
        *uDst.pb++ = *uSrc.pb++;

    return uDst.pv;
}

