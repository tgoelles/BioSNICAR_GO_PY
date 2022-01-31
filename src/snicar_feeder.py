import collections as c
import math

import numpy as np
import pandas as pd
import xarray as xr
from scipy.interpolate import pchip
import toon_rt_solver as toon_solver
import adding_doubling_solver as adding_doubling
import mie_coated_water_spheres as wcs


def snicar_feeder(Inputs):

    """
    This script takes the user defined Inputs from the driver script and
    calculates te relevant tau (optical thickness), ssa
    (single scattering albedo) and g (asymmetry parameter) for each
    vertical layer to send to the radiative transfer solver.

    There are two options for the radiative transfer solver A) the fast
    tridiaginal matrix method of toon et al. (1989) which is very efficient
    but limited to granular layers or B) the adding-doubling method that
    can include bubbly ice layers and fresnel reflections anywhere
    in the column.

    For Mie calculations, this script makes the necessary ajustments
    for nonspherical grain shapes using the method of He et al. (2016).

    The script calls out to one of two radiative transfer solver scripts:
    adding_doubling_solver.py or two_stream_solver.py.

    """

    # load variables from input table


    files = [
        Inputs.file_soot1,
        Inputs.file_soot2,
        Inputs.file_brwnC1,
        Inputs.file_brwnC2,
        Inputs.file_dust1,
        Inputs.file_dust2,
        Inputs.file_dust3,
        Inputs.file_dust4,
        Inputs.file_dust5,
        Inputs.file_ash1,
        Inputs.file_ash2,
        Inputs.file_ash3,
        Inputs.file_ash4,
        Inputs.file_ash5,
        Inputs.file_ash_st_helens,
        Inputs.file_Skiles_dust1,
        Inputs.file_Skiles_dust2,
        Inputs.file_Skiles_dust3,
        Inputs.file_Skiles_dust4,
        Inputs.file_Skiles_dust5,
        Inputs.file_GreenlandCentral1,
        Inputs.file_GreenlandCentral2,
        Inputs.file_GreenlandCentral3,
        Inputs.file_GreenlandCentral4,
        Inputs.file_GreenlandCentral5,
        Inputs.file_Cook_Greenland_dust_L,
        Inputs.file_Cook_Greenland_dust_C,
        Inputs.file_Cook_Greenland_dust_H,
        Inputs.file_snw_alg,
        Inputs.file_glacier_algae,
    ]

    mass_concentrations = [
        Inputs.mss_cnc_soot1,
        Inputs.mss_cnc_soot2,
        Inputs.mss_cnc_brwnC1,
        Inputs.mss_cnc_brwnC2,
        Inputs.mss_cnc_dust1,
        Inputs.mss_cnc_dust2,
        Inputs.mss_cnc_dust3,
        Inputs.mss_cnc_dust4,
        Inputs.mss_cnc_dust5,
        Inputs.mss_cnc_ash1,
        Inputs.mss_cnc_ash2,
        Inputs.mss_cnc_ash3,
        Inputs.mss_cnc_ash4,
        Inputs.mss_cnc_ash5,
        Inputs.mss_cnc_ash_st_helens,
        Inputs.mss_cnc_Skiles_dust1,
        Inputs.mss_cnc_Skiles_dust2,
        Inputs.mss_cnc_Skiles_dust3,
        Inputs.mss_cnc_Skiles_dust4,
        Inputs.mss_cnc_Skiles_dust5,
        Inputs.mss_cnc_GreenlandCentral1,
        Inputs.mss_cnc_GreenlandCentral2,
        Inputs.mss_cnc_GreenlandCentral3,
        Inputs.mss_cnc_GreenlandCentral4,
        Inputs.mss_cnc_GreenlandCentral5,
        Inputs.mss_cnc_Cook_Greenland_dust_L,
        Inputs.mss_cnc_Cook_Greenland_dust_C,
        Inputs.mss_cnc_Cook_Greenland_dust_H,
        Inputs.mss_cnc_snw_alg,
        Inputs.mss_cnc_glacier_algae,
    ]

    # working Inputs.directories
    dir_spherical_ice_files = str(
        Inputs.dir_base + "Data/OP_data/480band/ice_spherical_grains/"
    )
    dir_hexagonal_ice_files = str(
        Inputs.dir_base + "Data/OP_data/480band/ice_hexagonal_columns/"
    )
    dir_lap_files = str(Inputs.dir_base + "Data/OP_data/480band/lap/")
    dir_bubbly_ice = str(Inputs.dir_base + "Data/OP_data/480band/bubbly_ice_files/")
    dir_fsds = str(Inputs.dir_base + "Data/OP_data/480band/fsds/")
    dir_ri_ice = str(Inputs.dir_base + "Data/OP_data/480band/")

    # retrieve nbr wvl, aer, layers and layer types
    temp = xr.open_dataset(str(dir_lap_files + "dust_greenland_Cook_LOW_20190911.nc"))
    wvl = np.array(temp["wvl"].values)
    wvl = wvl * 1e6
    nbr_wvl = len(wvl)
    Inputs.nbr_wvl = nbr_wvl
    Inputs.wvl = wvl

    # load incoming irradiance
    # calc cosine of solar zenith (radians)
    mu_not = np.cos(math.radians(np.rint(Inputs.solzen)))
    Inputs.mu_not = mu_not

    if Inputs.verbosity == 1:
        print("\ncosine of solar zenith = ", mu_not)

    flx_slr = []

    if Inputs.direct:

        coszen = str("SZA" + str(Inputs.solzen).rjust(2, "0"))

        if Inputs.incoming_i == 0:
            incoming_file = xr.open_dataset(
                str(dir_fsds + "swnb_480bnd_mlw_clr_" + coszen + ".nc")
            )
            if Inputs.verbosity == 1:
                print("atmospheric profile = mid-lat winter")
        elif Inputs.incoming_i == 1:
            incoming_file = xr.open_dataset(
                str(dir_fsds + "swnb_480bnd_mls_clr_" + coszen + ".nc")
            )
            if Inputs.verbosity == 1:
                print("atmospheric profile = mid-lat summer")
        elif Inputs.incoming_i == 2:
            incoming_file = xr.open_dataset(
                str(dir_fsds + "swnb_480bnd_saw_clr_" + coszen + ".nc")
            )
            print("atmospheric profile = sub-Arctic winter")
        elif Inputs.incoming_i == 3:
            incoming_file = xr.open_dataset(
                str(dir_fsds + "swnb_480bnd_sas_clr_" + coszen + ".nc")
            )
            if Inputs.verbosity == 1:
                print("atmospheric profile = sub-Arctic summer")
        elif Inputs.incoming_i == 4:
            incoming_file = xr.open_dataset(
                str(dir_fsds + "swnb_480bnd_smm_clr_" + coszen + ".nc")
            )
            if Inputs.verbosity == 1:
                print("atmospheric profile = Summit Station")
        elif Inputs.incoming_i == 5:
            incoming_file = xr.open_dataset(
                str(dir_fsds + "swnb_480bnd_hmn_clr_" + coszen + ".nc")
            )
            if Inputs.verbosity == 1:
                print("atmospheric profile = High Mountain")
        elif Inputs.incoming_i == 6:
            incoming_file = xr.open_dataset(str(dir_fsds + "swnb_480bnd_toa_clr.nc"))
            if Inputs.verbosity == 1:
                print("atmospheric profile = top-of-atmosphere")

        else:
            raise ValueError("Invalid choice of atmospheric profile")

        # flx_dwn_sfc is the spectral irradiance in W m-2 and is
        # pre-calculated (flx_frc_sfc*flx_bb_sfc in original code)
        flx_slr = incoming_file["flx_dwn_sfc"].values
        flx_slr[flx_slr <= 0] = 1e-30
        Inputs.flx_slr = flx_slr
        Inputs.Fs = flx_slr / (mu_not * np.pi)
        Inputs.Fd = np.zeros(nbr_wvl)

    else:

        if Inputs.incoming_i == 0:

            incoming_file = xr.open_dataset(str(dir_fsds + "swnb_480bnd_mlw_cld.nc"))
        elif Inputs.incoming_i == 1:
            incoming_file = xr.open_dataset(str(dir_fsds + "swnb_480bnd_mls_cld.nc"))
        elif Inputs.incoming_i == 2:
            incoming_file = xr.open_dataset(str(dir_fsds + "swnb_480bnd_saw_cld.nc"))
        elif Inputs.incoming_i == 3:
            incoming_file = xr.open_dataset(str(dir_fsds + "swnb_480bnd_sas_cld.nc"))
        elif Inputs.incoming_i == 4:
            incoming_file = xr.open_dataset(str(dir_fsds + "swnb_480bnd_smm_cld.nc"))
        elif Inputs.incoming_i == 5:
            incoming_file = xr.open_dataset(str(dir_fsds + "swnb_480bnd_hmn_cld.nc"))
        elif Inputs.incoming_i == 6:
            incoming_file = xr.open_dataset(str(dir_fsds + "swnb_480bnd_toa_cld.nc"))

        else:
            raise ValueError("Invalid choice of atmospheric profile")

        flx_slr = incoming_file["flx_dwn_sfc"].values
        flx_slr[flx_slr <= 0] = 1e-30
        Inputs.flx_slr = flx_slr
        Inputs.Fd = flx_slr / (mu_not * np.pi)
        Inputs.Fs = np.zeros(nbr_wvl)

    # ----------------------------------------------------------------------------------
    # Read in ice optical properties
    # ----------------------------------------------------------------------------------
    # set up empty arrays
    ssa_snw = np.empty([Inputs.nbr_lyr, nbr_wvl])
    MAC_snw = np.empty([Inputs.nbr_lyr, nbr_wvl])
    g_snw = np.empty([Inputs.nbr_lyr, nbr_wvl])
    abs_cff_mss_ice = np.empty([nbr_wvl])

    # load refractive index of bubbly ice + Inputs.directory for granular OPs
    refidx_file = xr.open_dataset(dir_ri_ice + "rfidx_ice.nc")
    fresnel_diffuse_file = xr.open_dataset(dir_ri_ice + "fl_reflection_diffuse.nc")
    if Inputs.rf_ice == 0:
        dir_op = "ice_Wrn84/ice_Wrn84_"
        if Inputs.verbosity == 1:
            print("Using Warren 84 refractive index")
        refidx_re = refidx_file["re_Wrn84"].values
        refidx_im = refidx_file["im_Wrn84"].values
        fl_r_dif_a = fresnel_diffuse_file["R_dif_fa_ice_Wrn84"].values
        fl_r_dif_b = fresnel_diffuse_file["R_dif_fb_ice_Wrn84"].values

    elif Inputs.rf_ice == 1:
        dir_op = "ice_Wrn08/ice_Wrn08_"
        if Inputs.verbosity == 1:
            print("Using Warren 08 refractive index")
        refidx_re = refidx_file["re_Wrn08"].values
        refidx_im = refidx_file["im_Wrn08"].values
        fl_r_dif_a = fresnel_diffuse_file["R_dif_fa_ice_Wrn08"].values
        fl_r_dif_b = fresnel_diffuse_file["R_dif_fb_ice_Wrn08"].values

    elif Inputs.rf_ice == 2:
        dir_op = "ice_Pic16/ice_Pic16_"
        if Inputs.verbosity == 1:
            print("Using Picard 16 refractive index")
        refidx_re = refidx_file["re_Pic16"].values
        refidx_im = refidx_file["im_Pic16"].values
        fl_r_dif_a = fresnel_diffuse_file["R_dif_fa_ice_Pic16"].values
        fl_r_dif_b = fresnel_diffuse_file["R_dif_fb_ice_Pic16"].values

    Inputs.refidx_re = refidx_re
    Inputs.refidx_im = refidx_im
    Inputs.fl_r_dif_a = fl_r_dif_a
    Inputs.fl_r_dif_b = fl_r_dif_b

    # calculations of ice OPs in each layer
    for i in np.arange(0, Inputs.nbr_lyr, 1):

        if Inputs.verbosity == 1:
            print(f"\nLayer: {i}")

        if Inputs.layer_type[i] == 0:  # granular layer
            # load ice file from dir depending on grain shape and size
            if Inputs.grain_rds[i] == 0:
                raise ValueError("ERROR: ICE GRAIN RADIUS SET TO ZERO")

            if Inputs.grain_shp[i] == 4:  # large hex prisms (geometric optics)
                file_ice = str(
                    dir_hexagonal_ice_files
                    + dir_op
                    + "{}_{}.nc".format(
                        str(Inputs.side_length[i]).rjust(4, "0"), str(Inputs.depth[i])
                    )
                )
                if Inputs.verbosity == 1:
                    print(
                        "Using hex col w side length = {}, length = {}".format(
                            str(Inputs.side_length[i]).rjust(4, "0"), str(Inputs.depth[i])
                        )
                    )

            elif Inputs.grain_shp[i] < 4:
                file_ice = str(
                    dir_spherical_ice_files
                    + dir_op
                    + "{}.nc".format(str(Inputs.grain_rds[i]).rjust(4, "0"))
                )

                if Inputs.verbosity == 1:
                    print(
                        "Using Mie mode: spheres w radius = {}".format(
                            str(Inputs.grain_rds[i]).rjust(4, "0")
                        )
                    )

            # if liquid water coatings are applied
            if Inputs.rwater[i] > Inputs.grain_rds[i]:

                if Inputs.grain_shp[i] != 0:
                    raise ValueError("Water coating can only be applied to spheres")

                # water coating calculations (coated spheres)
                fn_ice = Inputs.dir_base + "/Data/OP_data/480band/rfidx_ice.nc"
                fn_water = (
                    Inputs.dir_base
                    + "Data/OP_data/Refractive_Index_Liquid_Water_Segelstein_1981.csv"
                )
                res = wcs.miecoated_driver(
                    rice=Inputs.grain_rds[i],
                    rwater=Inputs.rwater[i],
                    fn_ice=fn_ice,
                    rf_ice=Inputs.rf_ice,
                    fn_water=fn_water,
                    wvl=wvl,
                )

                ssa_snw[i, :] = res["ssa"]
                g_snw[i, :] = res["asymmetry"]

                with xr.open_dataset(file_ice) as temp:
                    ext_cff_mss = temp["ext_cff_mss"].values
                    MAC_snw[i, :] = ext_cff_mss

            else:

                with xr.open_dataset(file_ice) as temp:

                    ssa = temp["ss_alb"].values
                    ssa_snw[i, :] = ssa
                    ext_cff_mss = temp["ext_cff_mss"].values
                    MAC_snw[i, :] = ext_cff_mss
                    asm_prm = temp["asm_prm"].values

                    g_snw[i, :] = asm_prm

                    # Correct g for aspherical particles - He et al.(2017)
                    # Applies only when Inputs.grain_shp!=0
                    # g_snw asymmetry factor parameterization coefficients
                    # (6 bands) from Table 3 & Eqs. 6-7 in He et al. (2017)
                    # assume same values for 4-5 um band, which leads
                    # to very small biases (<3%)

                    if (Inputs.grain_shp[i] > 0) & (Inputs.grain_shp[i] < 4):

                        g_wvl = np.array(
                            [0.25, 0.70, 1.41, 1.90, 2.50, 3.50, 4.00, 5.00]
                        )
                        g_wvl_center = (
                            np.array(g_wvl[1:8]) / 2 + np.array(g_wvl[0:7]) / 2
                        )
                        g_b0 = np.array(
                            [
                                9.76029e-01,
                                9.67798e-01,
                                1.00111e00,
                                1.00224e00,
                                9.64295e-01,
                                9.97475e-01,
                                9.97475e-01,
                            ]
                        )
                        g_b1 = np.array(
                            [
                                5.21042e-01,
                                4.96181e-01,
                                1.83711e-01,
                                1.37082e-01,
                                5.50598e-02,
                                8.48743e-02,
                                8.48743e-02,
                            ]
                        )
                        g_b2 = np.array(
                            [
                                -2.66792e-04,
                                1.14088e-03,
                                2.37011e-04,
                                -2.35905e-04,
                                8.40449e-04,
                                -4.71484e-04,
                                -4.71484e-04,
                            ]
                        )

                        # Tables 1 & 2 and Eqs. 3.1-3.4 from Fu, 2007
                        g_f07_c2 = np.array(
                            [
                                1.349959e-1,
                                1.115697e-1,
                                9.853958e-2,
                                5.557793e-2,
                                -1.233493e-1,
                                0.0,
                                0.0,
                            ]
                        )
                        g_f07_c1 = np.array(
                            [
                                -3.987320e-1,
                                -3.723287e-1,
                                -3.924784e-1,
                                -3.259404e-1,
                                4.429054e-2,
                                -1.726586e-1,
                                -1.726586e-1,
                            ]
                        )
                        g_f07_c0 = np.array(
                            [
                                7.938904e-1,
                                8.030084e-1,
                                8.513932e-1,
                                8.692241e-1,
                                7.085850e-1,
                                6.412701e-1,
                                6.412701e-1,
                            ]
                        )
                        g_f07_p2 = np.array(
                            [
                                3.165543e-3,
                                2.014810e-3,
                                1.780838e-3,
                                6.987734e-4,
                                -1.882932e-2,
                                -2.277872e-2,
                                -2.277872e-2,
                            ]
                        )
                        g_f07_p1 = np.array(
                            [
                                1.140557e-1,
                                1.143152e-1,
                                1.143814e-1,
                                1.071238e-1,
                                1.353873e-1,
                                1.914431e-1,
                                1.914431e-1,
                            ]
                        )
                        g_f07_p0 = np.array(
                            [
                                5.292852e-1,
                                5.425909e-1,
                                5.601598e-1,
                                6.023407e-1,
                                6.473899e-1,
                                4.634944e-1,
                                4.634944e-1,
                            ]
                        )
                        fs_hex = 0.788  # shape factor for hex plate

                        # eff grain diameter
                        diam_ice = 2.0 * Inputs.grain_rds[i] / 0.544

                        if Inputs.shp_fctr[i] == 0:
                            # default shape factor for koch snowflake;
                            # He et al. (2017), Table 1
                            fs_koch = 0.712

                        else:

                            fs_koch = Inputs.shp_fctr[i]

                        if Inputs.grain_ar[i] == 0:
                            # default aspect ratio for koch
                            # snowflake; He et al. (2017), Table 1
                            ar_tmp = 2.5

                        else:

                            ar_tmp = Inputs.grain_ar[i]

                        # Eq.7, He et al. (2017)
                        g_snw_cg_tmp = (
                            g_b0 * (fs_koch / fs_hex) ** g_b1 * diam_ice ** g_b2
                        )

                        # Eqn. 3.3 in Fu (2007)
                        gg_snw_f07_tmp = (
                            g_f07_p0
                            + g_f07_p1 * np.log(ar_tmp)
                            + g_f07_p2 * (np.log(ar_tmp)) ** 2
                        )

                        # 1 = spheroid, He et al. (2017)
                        if Inputs.grain_shp[i] == 1:

                            # effective snow grain diameter
                            diam_ice = 2.0 * Inputs.grain_rds[i]

                            # default shape factor for spheroid;
                            # He et al. (2017), Table 1
                            if Inputs.shp_fctr[i] == 0:

                                fs_sphd = 0.929

                            else:
                                # if shp_factor not 0,
                                # then use user-defined value
                                fs_sphd = Inputs.shp_fctr[i]

                            if Inputs.grain_ar[i] == 0:
                                # default aspect ratio for spheroid;
                                # He et al. (2017), Table 1
                                ar_tmp = 0.5

                            else:

                                ar_tmp = Inputs.grain_ar[i]

                            # Eq.7, He et al. (2017)
                            g_snw_cg_tmp = (
                                g_b0 * (fs_sphd / fs_hex) ** g_b1 * diam_ice ** g_b2
                            )

                            # Eqn. 3.1 in Fu (2007)
                            gg_snw_F07_tmp = (
                                g_f07_c0 + g_f07_c1 * ar_tmp + g_f07_c2 * ar_tmp ** 2
                            )

                        # 3=hexagonal plate,
                        # He et al. 2017 parameterization
                        if Inputs.grain_shp[i] == 2:

                            # effective snow grain diameter
                            diam_ice = 2.0 * Inputs.grain_rds[i]

                            if Inputs.shp_fctr[i] == 0:
                                # default shape factor for
                                # hexagonal plates;
                                # He et al. (2017), Table 1
                                fs_hex0 = 0.788

                            else:

                                fs_hex0 = Inputs.shp_fctr[i]

                            if Inputs.grain_ar[i] == 0:
                                # default aspect ratio
                                # for hexagonal plate;
                                # He et al. (2017), Table 1
                                ar_tmp = 2.5

                            else:

                                ar_tmp = Inputs.grain_ar[i]

                            # Eq.7, He et al. (2017)
                            g_snw_cg_tmp = (
                                g_b0 * (fs_hex0 / fs_hex) ** g_b1 * diam_ice ** g_b2
                            )

                            # Eqn. 3.3 in Fu (2007)
                            gg_snw_F07_tmp = (
                                g_f07_p0
                                + g_f07_p1 * np.log(ar_tmp)
                                + g_f07_p2 * (np.log(ar_tmp)) ** 2
                            )

                        # 4=koch snowflake,
                        # He et al. (2017)
                        #  parameterization
                        if Inputs.grain_shp[i] == 3:

                            # effective snow grain diameter
                            diam_ice = 2.0 * Inputs.grain_rds[i] / 0.544

                            if Inputs.shp_fctr[i] == 0:
                                # default shape factor
                                # for koch snowflake;
                                # He et al. (2017), Table 1
                                fs_koch = 0.712

                            else:

                                fs_koch = Inputs.shp_fctr[i]

                            # default aspect ratio for
                            # koch snowflake; He et al. (2017), Table 1
                            if Inputs.grain_ar[i] == 0:

                                ar_tmp = 2.5

                            else:

                                ar_tmp = Inputs.grain_ar[i]

                            # Eq.7, He et al. (2017)
                            g_snw_cg_tmp = (
                                g_b0 * (fs_koch / fs_hex) ** g_b1 * diam_ice ** g_b2
                            )

                            # Eqn. 3.3 in Fu (2007)
                            gg_snw_F07_tmp = (
                                g_f07_p0
                                + g_f07_p1 * np.log(ar_tmp)
                                + g_f07_p2 * (np.log(ar_tmp)) ** 2
                            )

                        # 6 wavelength bands for g_snw to be
                        # interpolated into 480-bands of SNICAR
                        # shape-preserving piecewise interpolation
                        # into 480-bands
                        g_Cg_intp = pchip(g_wvl_center, g_snw_cg_tmp)(wvl)
                        gg_f07_intp = pchip(g_wvl_center, gg_snw_F07_tmp)(wvl)
                        g_snw_F07 = (
                            gg_f07_intp + (1.0 - gg_f07_intp) / ssa_snw[i, :] / 2
                        )  # Eq.2.2 in Fu (2007)
                        # Eq.6, He et al. (2017)
                        g_snw[i, :] = g_snw_F07 * g_Cg_intp
                        g_snw[i, 381:480] = g_snw[i, 380]
                        # assume same values for 4-5 um band,
                        # with v small biases (<3%)

                    g_snw[g_snw <= 0] = 0.00001
                    g_snw[g_snw > 0.99] = 0.99  # avoid unreasonable
                    # values (so far only occur in large-size spheroid cases)

        else:  # solid ice layer (Inputs.layer_type == 1)

            if Inputs.cdom_layer[i]:
                cdom_refidx_im = np.array(
                    pd.read_csv(dir_ri_ice + "k_cdom_240_750.csv")
                ).flatten()

                # rescale to SNICAR resolution
                cdom_refidx_im_rescaled = cdom_refidx_im[::10]
                refidx_im[3:54] = np.fmax(refidx_im[3:54], cdom_refidx_im_rescaled)

            rd = f"{Inputs.grain_rds[i]}"
            rd = rd.rjust(4, "0")
            file_ice = str(dir_bubbly_ice + "bbl_{}.nc").format(rd)
            file = xr.open_dataset(file_ice)
            sca_cff_vlm = file["sca_cff_vlm"].values
            g_snw[i, :] = file["asm_prm"].values
            abs_cff_mss_ice[:] = ((4 * np.pi * refidx_im) / (wvl * 1e-6)) / 917
            vlm_frac_air = (917 - Inputs.rho_layers[i]) / 917
            MAC_snw[i, :] = (
                (sca_cff_vlm * vlm_frac_air) / Inputs.rho_layers[i]
            ) + abs_cff_mss_ice
            ssa_snw[i, :] = ((sca_cff_vlm * vlm_frac_air) / Inputs.rho_layers[i]) / MAC_snw[
                i, :
            ]

    # ----------------------------------------------------------------------------------
    # Read in impurity optical properties
    # ----------------------------------------------------------------------------------

    # Load optical properties ssa, MAC and g
    # (one row per impurity, one column per wvalengths)
    # Load mass concentrations MSS per layer
    # (one row per layer, one column per impurity)

    ssa_aer = np.zeros([Inputs.nbr_aer, nbr_wvl])
    mac_aer = np.zeros([Inputs.nbr_aer, nbr_wvl])
    g_aer = np.zeros([Inputs.nbr_aer, nbr_wvl])
    mss_aer = np.zeros([Inputs.nbr_lyr, Inputs.nbr_aer])

    for aer in range(Inputs.nbr_aer):

        impurity_properties = xr.open_dataset(str(dir_lap_files + files[aer]))

        g_aer[aer, :] = impurity_properties["asm_prm"].values
        ssa_aer[aer, :] = impurity_properties["ss_alb"].values

        # coated particles: use ext_cff_mss_ncl for MAC
        if files[aer] == Inputs.file_brwnC2 or files[aer] == Inputs.file_soot2:
            mac_aer[aer, :] = impurity_properties["ext_cff_mss_ncl"].values

        else:
            mac_aer[aer, :] = impurity_properties["ext_cff_mss"].values

        if files[aer] == Inputs.file_glacier_algae:
            # if GA_units == 1, GA concentration provided in cells/mL
            # mss_aer should be in cells/kg
            # thus mss_aer is divided by kg/mL ice = 917*10**(-6)
            # with density of ice 917 kg m3
            if Inputs.GA_units == 1:

                mss_aer[0:Inputs.nbr_lyr, aer] = np.array(mass_concentrations[aer]) / (
                    917 * 10 ** (-6)
                )

            else:
                mss_aer[0:Inputs.nbr_lyr, aer] = np.array(mass_concentrations[aer]) * 1e-9

        elif files[aer] == Inputs.file_snw_alg:
            # if SA_units == 1, SA concentration provided in cells/mL
            # but mss_aer should be in cells/kg
            # thus mss_aer is divided by kg/mL ice = 917*10**(-6)
            # with density of ice 917 kg m3
            if Inputs.SA_units == 1:
                mss_aer[0:Inputs.nbr_lyr, aer] = np.array(mass_concentrations[aer]) / (
                    917 * 10 ** (-6)
                )

            else:
                mss_aer[0:Inputs.nbr_lyr, aer] = np.array(mass_concentrations[aer]) * 1e-9

        else:
            # conversion to kg/kg ice from ng/g
            mss_aer[0:Inputs.nbr_lyr, aer] = np.array(mass_concentrations[aer]) * 1e-9

        # if c_factor provided, then mss_aer multiplied by c_factor
        if (
            files[aer] == Inputs.file_glacier_algae
            and isinstance(Inputs.c_factor_GA, (int, float))
            and (Inputs.c_factor_GA > 0)
        ):
            mss_aer[0:Inputs.nbr_lyr, aer] = Inputs.c_factor_GA * mss_aer[0:Inputs.nbr_lyr, aer]

        if (
            files[aer] == Inputs.file_snw_alg
            and isinstance(Inputs.c_factor_SA, (int, float))
            and (Inputs.c_factor_SA > 0)
        ):
            mss_aer[0:Inputs.nbr_lyr, aer] = Inputs.c_factor_SA * mss_aer[0:Inputs.nbr_lyr, aer]

    # ----------------------------------------------------------------------------------
    # Begin solving Radiative Transfer
    # -----------------------------------------------------------------------------------

    # 1. Calculate effective tau (optical Inputs.depth),
    # ssa (single scattering albedo) and
    # g (assymetry parameter) for the ice +
    # impurities mixture.

    # ssa and g for the individual components has
    # been calculated using Mie theory and
    # stored in a netcdf file. Here, these values
    # are combined to give an overall
    # ssa and g for the ice + impurity mixture

    # initialize arrays
    g_sum = np.zeros([Inputs.nbr_lyr, nbr_wvl])
    ssa_sum = np.zeros([Inputs.nbr_lyr, Inputs.nbr_aer, nbr_wvl])
    tau = np.zeros([Inputs.nbr_lyr, nbr_wvl])
    ssa = np.zeros([Inputs.nbr_lyr, nbr_wvl])
    g = np.zeros([Inputs.nbr_lyr, nbr_wvl])
    L_aer = np.zeros([Inputs.nbr_lyr, Inputs.nbr_aer])
    tau_aer = np.zeros([Inputs.nbr_lyr, Inputs.nbr_aer, nbr_wvl])
    tau_sum = np.zeros([Inputs.nbr_lyr, nbr_wvl])
    ssa_sum = np.zeros([Inputs.nbr_lyr, nbr_wvl])
    L_snw = np.zeros(Inputs.nbr_lyr)
    tau_snw = np.zeros([Inputs.nbr_lyr, nbr_wvl])

    # for each layer, the layer mass (L) is density * layer thickness
    # for each layer the optical Inputs.depth is
    # the layer mass * the mass extinction coefficient
    # first for the ice in each layer

    for i in range(Inputs.nbr_lyr):

        L_snw[i] = Inputs.rho_layers[i] * Inputs.dz[i]

        for j in range(Inputs.nbr_aer):

            # kg ice m-2 * cells kg-1 ice = cells m-2
            L_aer[i, j] = L_snw[i] * mss_aer[i, j]
            # cells m-2 * m2 cells-1
            tau_aer[i, j, :] = L_aer[i, j] * mac_aer[j, :]
            tau_sum[i, :] = tau_sum[i, :] + tau_aer[i, j, :]
            ssa_sum[i, :] = ssa_sum[i, :] + (tau_aer[i, j, :] * ssa_aer[j, :])
            g_sum[i, :] = g_sum[i, :] + (tau_aer[i, j, :] * ssa_aer[j, :] * g_aer[j, :])

            # ice mass = snow mass - impurity mass (generally tiny correction)
            # if aer == algae and L_aer is in cells m-2, should be converted
            # to m-2 kg-1 : 1 cell = 1ng = 10**(-12) kg

            if files[j] == Inputs.file_glacier_algae and Inputs.GA_units == 1:

                L_snw[i] = L_snw[i] - L_aer[i, j] * 10 ** (-12)

            elif files[j] == Inputs.file_snw_alg and Inputs.SA_units == 1:

                L_snw[i] = L_snw[i] - L_aer[i, j] * 10 ** (-12)

            else:

                L_snw[i] = L_snw[i] - L_aer[i, j]

        tau_snw[i, :] = L_snw[i] * MAC_snw[i, :]
        # finally, for each layer calculate the effective ssa, tau and g
        # for the snow+LAP
        tau[i, :] = tau_sum[i, :] + tau_snw[i, :]
        ssa[i, :] = (1 / tau[i, :]) * (ssa_sum[i, :] + (ssa_snw[i, :] * tau_snw[i, :]))
        g[i, :] = (1 / (tau[i, :] * (ssa[i, :]))) * (
            g_sum[i, :] + (g_snw[i, :] * ssa_snw[i, :] * tau_snw[i, :])
        )

    Inputs.tau = tau
    Inputs.ssa = ssa
    Inputs.g = g
    Inputs.L_snw = L_snw

    # just in case any unrealistic values arise (none detected so far)
    ssa[ssa <= 0] = 0.00000001
    ssa[ssa >= 1] = 0.99999999
    g[g <= 0] = 0.00001
    g[g >= 1] = 0.99999

    Inputs.tau = tau
    Inputs.ssa = ssa
    Inputs.g = g
    Inputs.L_snw = L_snw

    # CALL RT SOLVER (toon_solver  = toon ET AL, TRIDIAGONAL MATRIX METHOD;
    # add_double = ADDING-DOUBLING METHOD)

    Outputs = c.namedtuple(
        "Outputs",
        ["wvl", "albedo", "BBA", "BBAVIS", "BBANIR", "abs_slr", "heat_rt", "abs_ice"],
    )

    if Inputs.toon:

        (
            Outputs.wvl,
            Outputs.albedo,
            Outputs.BBA,
            Outputs.BBAVIS,
            Outputs.BBANIR,
            Outputs.abs_slr,
            Outputs.heat_rt,
        ) = toon_solver.toon_solver(Inputs)

    if Inputs.add_double:

        (
            Outputs.wvl,
            Outputs.albedo,
            Outputs.BBA,
            Outputs.BBAVIS,
            Outputs.BBANIR,
            Outputs.abs_slr,
            Outputs.heat_rt,
        ) = adding_doubling.adding_doubling_solver(Inputs)

    return Outputs
